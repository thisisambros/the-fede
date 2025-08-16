"""Claude Code SDK client for The Fede bot."""

import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

from ..utils.config import Settings
from .personality import get_conversation_prompt
from .prompts import CONVERSATION_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Claude Code SDK client with full capabilities including images and tools."""
    
    def __init__(self, settings: Settings) -> None:
        """Initialize Claude client with settings.
        
        Args:
            settings: Application settings containing API keys and configuration
        """
        self.settings = settings
        self.temp_dir = Path(tempfile.gettempdir()) / "fede_images"
        self.temp_dir.mkdir(exist_ok=True)
        logger.info("Claude Code SDK initialized")
    
    def _build_mcp_servers(self) -> Dict[str, Any]:
        """Build MCP servers configuration.
        
        Returns:
            Dictionary of MCP server configurations
        """
        mcp_servers = {}
        
        # Always enable Google Calendar
        mcp_servers["google-calendar"] = {
            "command": "npx",
            "args": ["-y", "@cocal/google-calendar-mcp"],
            "env": {
                "GOOGLE_OAUTH_CREDENTIALS": "/Users/lambrosini/Downloads/client_secret_2_843378804649-km2o97dnf7rporuqlj51p79calnffkru.apps.googleusercontent.com.json"
            }
        }
        
        # Always enable Gmail
        mcp_servers["gmail"] = {
            "command": "npx",
            "args": ["-y", "@gongrzhe/server-gmail-autoauth-mcp"]
        }
        
        logger.info("Google Calendar and Gmail MCP servers enabled")
        
        return mcp_servers
    
    def _create_options(self, context: Optional[Dict] = None) -> ClaudeCodeOptions:
        """Create Claude Code options.
        
        Args:
            context: Optional context dictionary for the conversation
            
        Returns:
            Configured ClaudeCodeOptions instance
        """
        mcp_servers = self._build_mcp_servers()
        
        # Always allow Google Calendar and Gmail tools
        allowed_tools = ["mcp__google-calendar", "mcp__gmail"]
        
        return ClaudeCodeOptions(
            system_prompt=get_conversation_prompt(context),
            permission_mode='default',
            mcp_servers=mcp_servers,
            allowed_tools=allowed_tools
        )
    
    async def _process_messages(self, client: ClaudeSDKClient) -> Tuple[str, Optional[Dict]]:
        """Process messages from Claude SDK.
        
        Args:
            client: Active ClaudeSDKClient instance
            
        Returns:
            Tuple of (response_text, metadata_dict)
        """
        full_response = ""
        result_data = None
        
        async for message in client.receive_messages():
            message_type = type(message).__name__
            
            if message_type == "AssistantMessage":
                if hasattr(message, 'content'):
                    content = message.content
                    if isinstance(content, list):
                        for item in content:
                            if hasattr(item, 'text'):
                                full_response += item.text
                            elif isinstance(item, dict) and 'text' in item:
                                full_response += item['text']
                    elif isinstance(content, str):
                        full_response += content
            
            elif message_type == "ResultMessage":
                if hasattr(message, 'result'):
                    full_response = message.result
                
                result_data = {
                    "success": getattr(message, 'subtype', '') == "success",
                    "cost": getattr(message, 'total_cost_usd', 0),
                    "duration": getattr(message, 'duration_ms', 0),
                    "turns": getattr(message, 'num_turns', 1)
                }
                break
        
        if result_data and logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Query completed in {result_data['duration']}ms, cost: ${result_data['cost']:.4f}")
        
        return full_response, result_data
    
    async def analyze_image(
        self,
        image_bytes: bytes,
        prompt: str = "What's in this image?",
        media_type: str = "image/jpeg",
        context: Optional[Dict] = None
    ) -> str:
        """Analyze an image using Claude SDK's Read tool.
        
        Args:
            image_bytes: Raw image data
            prompt: Analysis prompt
            media_type: MIME type of the image
            context: Optional conversation context
            
        Returns:
            Analysis result as string
            
        Raises:
            Exception: If image analysis fails
        """
        try:
            # Save image to temporary file
            file_ext = ".jpg" if "jpeg" in media_type else ".png"
            temp_file = self.temp_dir / f"img_{hash(image_bytes)}{file_ext}"
            temp_file.write_bytes(image_bytes)
            
            try:
                # Build query based on prompt type
                if "conversation" in prompt.lower() or "chat" in prompt.lower():
                    query = f"Analyze the conversation screenshot at {temp_file}\n\n{CONVERSATION_ANALYSIS_PROMPT}"
                else:
                    query = f"{prompt}\n\nAnalyze the image at: {temp_file}"
                
                # Create options and client
                options = self._create_options(context)
                
                async with ClaudeSDKClient(options) as client:
                    await client.query(query)
                    response, _ = await self._process_messages(client)
                    return response or "Analysis complete."
                    
            finally:
                # Clean up temp file
                try:
                    temp_file.unlink()
                except Exception:
                    pass
                
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            raise
    
    async def send_message(
        self,
        messages: List[Dict[str, Any]],
        context: Optional[Dict] = None,
        stream: bool = False,
        session_id: Optional[str] = None,
    ) -> str:
        """Send messages to Claude SDK.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            context: Optional conversation context
            stream: Whether to stream responses (not implemented)
            session_id: Optional session ID for tracking
            
        Returns:
            Claude's response as string
            
        Raises:
            Exception: If message sending fails
        """
        try:
            # Build conversation query
            query = self._build_query(messages)
            
            # Create options and client
            options = self._create_options(context)
            
            async with ClaudeSDKClient(options) as client:
                await client.query(query)
                response, _ = await self._process_messages(client)
                return response or "I understand. How can I help?"
                
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise
    
    def _build_query(self, messages: List[Dict[str, Any]]) -> str:
        """Build a query string from messages.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Formatted query string
        """
        query_parts = []
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            if isinstance(content, str):
                query_parts.append(f"{role.title()}: {content}")
            else:
                # Handle complex content with images
                for part in content:
                    if part.get("type") == "text":
                        query_parts.append(f"{role.title()}: {part['text']}")
        
        return "\n\n".join(query_parts)
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.
        
        Args:
            text: Input text
            
        Returns:
            Estimated token count
        """
        # Rough estimation: ~4 characters per token
        return len(text) // 4