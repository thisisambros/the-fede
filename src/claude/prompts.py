"""Specialized prompts for Claude image analysis."""

CONVERSATION_ANALYSIS_PROMPT = """
Analyze this screenshot of a conversation. Please extract and provide:

1. **CONVERSATION METADATA:**
   - App/Platform (WhatsApp, Telegram, iMessage, etc.)
   - Contact name (usually shown at the top)
   - Time/date information visible
   
2. **PARTICIPANTS:**
   - Messages on the RIGHT side = User (Ambros/the person showing the screenshot)
   - Messages on the LEFT side = Other person (extract their name from the header)
   
3. **CONVERSATION FLOW:**
   - Summarize what each person is saying
   - Note any commitments, plans, or requests
   
4. **ACTIONABLE ITEMS:**
   Identify any actions needed:
   - Meetings/appointments to schedule (with WHO, WHEN, WHERE)
   - Messages to send or reply to
   - Tasks to complete
   - Information to remember
   
5. **EXTRACTED DATA:**
   Pull out specific details:
   - Names mentioned
   - Dates/times mentioned
   - Locations mentioned
   - Phone numbers or emails
   - Any other relevant data

Format your response clearly with these sections. Be specific about WHO is involved in any actions.
"""

GENERAL_IMAGE_PROMPT = """
Analyze this image and describe what you see. If it contains text, transcribe it. 
If it shows any actionable items (calendar events, emails, tasks), identify them clearly.
"""