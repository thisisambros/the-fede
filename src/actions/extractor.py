"""Extract actionable items from Claude's analysis."""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ActionItem:
    """Represents an action to be taken.
    
    Attributes:
        action_type: Type of action (calendar_event, email, todo, etc.)
        parameters: Dictionary of parameters needed for the action
        requires_confirmation: Whether user confirmation is required
        confidence: Confidence score for the extracted action (0.0 to 1.0)
        context: Additional context like participants, platform, etc.
    """
    action_type: str
    parameters: Dict[str, Any]
    requires_confirmation: bool = True
    confidence: float = 0.0
    context: Optional[Dict[str, Any]] = field(default_factory=dict)


class ActionExtractor:
    """Extract and parse actionable items from text."""
    
    def __init__(self) -> None:
        """Initialize the action extractor with regex patterns for different action types."""
        self.patterns = {
            'calendar_event': [
                r'meeting.*?(?:on|at|for)\s+(.+?)(?:\.|$)',
                r'schedule.*?(?:on|at|for)\s+(.+?)(?:\.|$)',
                r'book.*?(?:on|at|for)\s+(.+?)(?:\.|$)',
                r'appointment.*?(?:on|at|for)\s+(.+?)(?:\.|$)',
            ],
            'email': [
                r'email\s+(.+?)\s+(?:about|regarding|with)\s+(.+?)(?:\.|$)',
                r'send\s+(?:an?\s+)?email\s+to\s+(.+?)(?:\.|$)',
                r'reply\s+to\s+(.+?)(?:\.|$)',
            ],
            'todo': [
                r'remind\s+me\s+(?:to\s+)?(.+?)(?:\.|$)',
                r'add\s+(?:a\s+)?(?:task|todo):\s*(.+?)(?:\.|$)',
                r'todo:\s*(.+?)(?:\.|$)',
            ]
        }
    
    def extract_from_analysis(self, text: str) -> List[ActionItem]:
        """Extract action items from Claude's analysis of an image or conversation.
        
        Args:
            text: The analysis text from Claude containing potential actions
            
        Returns:
            List of ActionItem objects representing extracted actions
        """
        actions = []
        
        # Extract conversation metadata if present
        conversation_context = self._extract_conversation_context(text)
        
        # Look for explicit action markers that Claude might include
        if "ACTIONABLE ITEMS:" in text or "Actions to take:" in text:
            actions.extend(self._parse_explicit_actions(text, conversation_context))
        
        # Look for implicit actions in the text
        actions.extend(self._parse_implicit_actions(text, conversation_context))
        
        return actions
    
    def _extract_conversation_context(self, text: str) -> Dict[str, str]:
        """Extract conversation metadata from analysis text.
        
        Args:
            text: The analysis text containing conversation metadata
            
        Returns:
            Dictionary containing extracted metadata (contact_name, platform, etc.)
        """
        context = {}
        
        # Extract contact name
        contact_pattern = r'Contact name[:\s]+([^\n]+)'
        contact_match = re.search(contact_pattern, text, re.IGNORECASE)
        if contact_match:
            context['contact_name'] = contact_match.group(1).strip()
        
        # Extract participants section
        if "PARTICIPANTS:" in text:
            participants_section = text.split("PARTICIPANTS:")[1].split("\n\n")[0]
            if "LEFT side" in participants_section:
                left_match = re.search(r'LEFT side[:\s]+=?\s*([^\n(]+)', participants_section)
                if left_match:
                    context['other_person'] = left_match.group(1).strip()
        
        # Extract platform
        platform_pattern = r'(?:App/Platform|Platform)[:\s]+([^\n]+)'
        platform_match = re.search(platform_pattern, text, re.IGNORECASE)
        if platform_match:
            context['platform'] = platform_match.group(1).strip()
        
        return context
    
    def _parse_explicit_actions(self, text: str, context: Optional[Dict[str, Any]] = None) -> List[ActionItem]:
        """Parse explicitly marked actions from text (e.g., JSON-formatted actions).
        
        Args:
            text: The text containing explicitly marked actions
            context: Optional conversation context to attach to actions
            
        Returns:
            List of ActionItem objects parsed from explicit markers
        """
        actions = []
        
        # Look for JSON-formatted actions
        json_pattern = r'```json\s*(\{.*?\})\s*```'
        json_matches = re.findall(json_pattern, text, re.DOTALL)
        
        for match in json_matches:
            try:
                data = json.loads(match)
                if 'action' in data or 'type' in data:
                    action = ActionItem(
                        action_type=data.get('action') or data.get('type'),
                        parameters=data.get('parameters', {}),
                        requires_confirmation=data.get('requires_confirmation', True),
                        confidence=data.get('confidence', 0.8),
                        context=context
                    )
                    actions.append(action)
            except json.JSONDecodeError:
                logger.debug(f"Could not parse JSON action: {match}")
        
        return actions
    
    def _parse_implicit_actions(self, text: str, context: Optional[Dict[str, Any]] = None) -> List[ActionItem]:
        """Parse implicit actions from natural language using regex patterns.
        
        Args:
            text: The text to search for implicit actions
            context: Optional conversation context to attach to actions
            
        Returns:
            List of ActionItem objects extracted from natural language
        """
        actions = []
        text_lower = text.lower()
        
        # Check for calendar events
        calendar_keywords = ['meeting', 'appointment', 'schedule', 'book', 'calendar']
        if any(keyword in text_lower for keyword in calendar_keywords):
            # Extract date/time mentions
            date_patterns = [
                r'(monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
                r'(tomorrow|today|next week)',
                r'(\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec))',
                r'(\d{1,2}:\d{2}\s*(?:am|pm)?)',
                r'(\d{1,2}\s*(?:am|pm))',
            ]
            
            dates = []
            times = []
            for pattern in date_patterns:
                matches = re.findall(pattern, text_lower)
                if matches:
                    if 'am' in pattern or 'pm' in pattern or ':' in pattern:
                        times.extend(matches)
                    else:
                        dates.extend(matches)
            
            if dates or times:
                params = {
                    'extracted_dates': dates,
                    'extracted_times': times,
                    'original_text': text[:500]  # Keep context
                }
                # Add participant info if available
                if context and context.get('other_person'):
                    params['suggested_attendee'] = context['other_person']
                
                action = ActionItem(
                    action_type='calendar_event',
                    parameters=params,
                    requires_confirmation=True,
                    confidence=0.7 if dates and times else 0.5,
                    context=context
                )
                actions.append(action)
        
        # Check for email mentions
        email_keywords = ['email', 'send', 'reply', 'message']
        if any(keyword in text_lower for keyword in email_keywords):
            # Look for email addresses
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, text)
            
            if emails or 'email' in text_lower:
                action = ActionItem(
                    action_type='email',
                    parameters={
                        'extracted_emails': emails,
                        'original_text': text[:500]
                    },
                    requires_confirmation=True,
                    confidence=0.6 if emails else 0.4
                )
                actions.append(action)
        
        # Check for todo items
        todo_keywords = ['todo', 'task', 'remind', 'remember', 'don\'t forget']
        if any(keyword in text_lower for keyword in todo_keywords):
            action = ActionItem(
                action_type='todo',
                parameters={
                    'original_text': text[:500]
                },
                requires_confirmation=True,
                confidence=0.5
            )
            actions.append(action)
        
        return actions
    
    def format_for_confirmation(self, action: ActionItem) -> str:
        """Format an action item for user confirmation.
        
        Args:
            action: The ActionItem to format
            
        Returns:
            Formatted string ready for display to the user
        """
        if action.action_type == 'calendar_event':
            dates = action.parameters.get('extracted_dates', [])
            times = action.parameters.get('extracted_times', [])
            attendee = action.parameters.get('suggested_attendee', '')
            
            msg = f"""📅 **Calendar Event Detected**
Dates mentioned: {', '.join(dates) if dates else 'None found'}
Times mentioned: {', '.join(times) if times else 'None found'}"""
            
            if attendee:
                msg += f"\nSuggested attendee: **{attendee}** (from conversation)"
            
            if action.context and action.context.get('platform'):
                msg += f"\nSource: {action.context['platform']} conversation"
            
            msg += """

To create this event, I need:
- Event title
- Exact date and time
- Duration
- Location (optional)
- Attendees (optional)

Should I help you create this calendar event?"""
            return msg
        
        elif action.action_type == 'email':
            emails = action.parameters.get('extracted_emails', [])
            return f"""✉️ **Email Action Detected**
Email addresses found: {', '.join(emails) if emails else 'None'}

To send this email, I need:
- Recipient email address
- Subject
- Message body

Should I help you draft this email?"""
        
        elif action.action_type == 'todo':
            return f"""✅ **Todo/Reminder Detected**

To add this task, I need:
- Task description
- Due date (optional)
- Priority (optional)

Should I add this to your todo list?"""
        
        return f"Action detected: {action.action_type}"