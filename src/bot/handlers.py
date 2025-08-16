"""Message handlers for the Telegram bot."""

import io
import logging
from typing import Optional

from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

from ..actions.extractor import ActionExtractor
from ..claude.client import ClaudeClient
from ..claude.prompts import CONVERSATION_ANALYSIS_PROMPT, GENERAL_IMAGE_PROMPT
from ..claude.session import SessionManager
from ..utils.config import Settings

logger = logging.getLogger(__name__)


class MessageHandlers:
    """Handle different types of Telegram messages."""

    def __init__(
        self,
        claude_client: ClaudeClient,
        session_manager: SessionManager,
        settings: Settings
    ) -> None:
        """Initialize message handlers with dependencies.
        
        Args:
            claude_client: Claude SDK client for AI interactions
            session_manager: Manager for conversation sessions
            settings: Application configuration settings
        """
        self.claude = claude_client
        self.sessions = session_manager
        self.settings = settings
        self.action_extractor = ActionExtractor()

    async def _check_authorization(self, update: Update) -> bool:
        """Check if user is authorized."""
        user_id = update.effective_user.id
        if user_id != self.settings.telegram_user_id:
            await update.effective_message.reply_text(
                "Sorry, you are not authorized to use this bot."
            )
            return False
        return True

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command - welcome new users.
        
        Args:
            update: The Telegram update containing the command
            context: The callback context
        """
        if not await self._check_authorization(update):
            return

        user_name = update.effective_user.first_name
        
        await update.effective_message.reply_text(
            f"Hello {user_name}! I'm Fede, your personal AI assistant.\n\n"
            "I can help you manage your digital life. Send me a message to get started!\n\n"
            "Commands:\n"
            "/help - Show available commands\n"
            "/new - Start a new conversation\n"
            "/end - End current conversation\n"
            "/status - Show session status\n"
            "/calendar - Show upcoming calendar events",
            parse_mode=ParseMode.MARKDOWN
        )

    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command - show available commands and features.
        
        Args:
            update: The Telegram update containing the command
            context: The callback context
        """
        if not await self._check_authorization(update):
            return

        help_text = """
*Fede - Personal AI Assistant*

*Commands:*
• /start - Start the bot
• /help - Show this help message
• /new - Start a fresh conversation
• /end - End and save current conversation
• /status - Show current session info
• /calendar - Show upcoming calendar events

*Features:*
• Send text messages for assistance
• Send screenshots for analysis
• Persistent conversation memory
• Pattern learning (with your permission)

*Available Integrations:*
• ✅ Google Calendar - List and manage events
• ✅ Gmail - Read and manage emails
• ✅ WhatsApp - Read and send messages

*Upcoming:*
• Custom todo list

Just send me a message to start chatting!
        """
        
        await update.effective_message.reply_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN
        )

    async def handle_new_session(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /new command to start a fresh conversation session.
        
        Ends the current session if one exists and creates a new one.
        
        Args:
            update: The Telegram update containing the command
            context: The callback context
        """
        if not await self._check_authorization(update):
            return

        user_id = update.effective_user.id
        
        # End current session if exists
        if self.sessions.current_session:
            await self.sessions.end_session(self.sessions.current_session["id"])
        
        # Create new session
        session_id = await self.sessions.get_or_create_session(user_id)
        
        await update.effective_message.reply_text(
            "Started a new conversation. How can I help you today?"
        )

    async def handle_end_session(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /end command to end the current conversation session.
        
        Args:
            update: The Telegram update containing the command
            context: The callback context
        """
        if not await self._check_authorization(update):
            return

        if self.sessions.current_session:
            await self.sessions.end_session(self.sessions.current_session["id"])
            await update.effective_message.reply_text(
                "Conversation ended. Send a message to start a new one."
            )
        else:
            await update.effective_message.reply_text(
                "No active conversation to end."
            )

    async def handle_calendar(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /calendar command - show upcoming calendar events.
        
        Args:
            update: The Telegram update containing the command
            context: The callback context
        """
        if not await self._check_authorization(update):
            return

        user_id = update.effective_user.id
        
        # Show typing indicator
        await update.effective_message.chat.send_action(ChatAction.TYPING)
        
        try:
            # Get or create session
            session_id = await self.sessions.get_or_create_session(user_id)
            
            # Get session context
            context_data = self.sessions.current_session.get("context", {})
            
            # Add user info to context if not present
            if "user_name" not in context_data:
                context_data["user_name"] = update.effective_user.first_name
                await self.sessions.update_context(session_id, context_data)
            
            # Query for calendar events
            calendar_query = "List my upcoming calendar events for the next 7 days. Format them nicely with date, time, and title."
            
            # Add user message to session
            await self.sessions.add_message(session_id, "user", calendar_query)
            
            # Get Claude's response using Calendar MCP
            messages = await self.sessions.get_messages(session_id)
            response = await self.claude.send_message(messages, context_data)
            
            # Add assistant message to session
            await self.sessions.add_message(session_id, "assistant", response)
            
            # Send response to user
            if len(response) > 4096:
                for i in range(0, len(response), 4096):
                    await update.effective_message.reply_text(
                        response[i:i+4096],
                        parse_mode=ParseMode.MARKDOWN
                    )
            else:
                await update.effective_message.reply_text(
                    response,
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logger.error(f"Error handling calendar command: {e}")
            await update.effective_message.reply_text(
                "Sorry, I couldn't fetch your calendar events. Please make sure the Google Calendar integration is properly configured."
            )
    
    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command - show current session information.
        
        Args:
            update: The Telegram update containing the command
            context: The callback context
        """
        if not await self._check_authorization(update):
            return

        user_id = update.effective_user.id
        
        if self.sessions.current_session:
            session_id = self.sessions.current_session["id"]
            messages = await self.sessions.get_messages(session_id, limit=100)
            message_count = len(messages)
            
            status_text = f"""
*Session Status*
• Session ID: {session_id}
• Messages: {message_count}
• Model: {self.settings.claude_model}
            """
        else:
            status_text = "No active session. Send a message to start."
        
        await update.effective_message.reply_text(
            status_text,
            parse_mode=ParseMode.MARKDOWN
        )

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle regular text messages from users.
        
        Processes the message through Claude SDK and returns the AI response.
        
        Args:
            update: The Telegram update containing the message
            context: The callback context
        """
        if not await self._check_authorization(update):
            return

        user_id = update.effective_user.id
        message_text = update.effective_message.text
        
        # Show typing indicator
        await update.effective_message.chat.send_action(ChatAction.TYPING)
        
        try:
            # Get or create session
            session_id = await self.sessions.get_or_create_session(user_id)
            
            # Add user message to session
            await self.sessions.add_message(session_id, "user", message_text)
            
            # Get conversation history
            messages = await self.sessions.get_messages(session_id)
            
            # Get session context
            context_data = self.sessions.current_session.get("context", {})
            
            # Add user info to context if not present
            if "user_name" not in context_data:
                context_data["user_name"] = update.effective_user.first_name
                await self.sessions.update_context(session_id, context_data)
            
            # Get Claude's response
            response = await self.claude.send_message(messages, context_data)
            
            # Add assistant message to session
            await self.sessions.add_message(session_id, "assistant", response)
            
            # Send response to user
            # Split long messages if needed
            if len(response) > 4096:
                for i in range(0, len(response), 4096):
                    await update.effective_message.reply_text(
                        response[i:i+4096],
                        parse_mode=ParseMode.MARKDOWN
                    )
            else:
                await update.effective_message.reply_text(
                    response,
                    parse_mode=ParseMode.MARKDOWN
                )
            
        except Exception as e:
            logger.error(f"Error handling text message: {e}")
            await update.effective_message.reply_text(
                "Sorry, I encountered an error processing your message. Please try again."
            )

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle photo messages including screenshots for analysis.
        
        Downloads the photo, analyzes it with Claude's vision capabilities,
        and extracts any actionable items from the analysis.
        
        Args:
            update: The Telegram update containing the photo
            context: The callback context
        """
        if not await self._check_authorization(update):
            return

        user_id = update.effective_user.id
        caption = update.effective_message.caption or "What's in this image?"
        
        await update.effective_message.chat.send_action(ChatAction.TYPING)
        
        try:
            # Get or create session
            session_id = await self.sessions.get_or_create_session(user_id)
            
            # Download the largest photo
            photo_file = await update.effective_message.photo[-1].get_file()
            photo_bytes = io.BytesIO()
            await photo_file.download_to_memory(photo_bytes)
            
            # Get the image bytes
            image_data = photo_bytes.getvalue()
            
            # Get session context
            context_data = self.sessions.current_session.get("context", {})
            
            # Add user info to context if not present
            if "user_name" not in context_data:
                context_data["user_name"] = update.effective_user.first_name
                await self.sessions.update_context(session_id, context_data)
            
            # Determine the type of analysis needed based on caption
            is_conversation = any(word in caption.lower() for word in 
                                 ['conversation', 'chat', 'message', 'whatsapp', 'telegram', 'imessage'])
            
            # Use appropriate prompt
            if is_conversation or caption.lower() == "what's in this image?":
                # Check if image might be a conversation screenshot
                analysis_prompt = CONVERSATION_ANALYSIS_PROMPT
            else:
                analysis_prompt = caption + "\n\n" + GENERAL_IMAGE_PROMPT
            
            # Analyze the image with Claude
            response = await self.claude.analyze_image(
                image_bytes=image_data,
                prompt=analysis_prompt,
                media_type="image/jpeg",
                context=context_data
            )
            
            # Add the interaction to session history
            # Store a placeholder for the image in history
            await self.sessions.add_message(
                session_id, 
                "user", 
                f"[Image uploaded] {caption}"
            )
            await self.sessions.add_message(session_id, "assistant", response)
            
            # Send the analysis response
            if len(response) > 4096:
                for i in range(0, len(response), 4096):
                    await update.effective_message.reply_text(
                        response[i:i+4096],
                        parse_mode=ParseMode.MARKDOWN
                    )
            else:
                await update.effective_message.reply_text(
                    response,
                    parse_mode=ParseMode.MARKDOWN
                )
            
            # Extract and present any actions found
            actions = self.action_extractor.extract_from_analysis(response)
            if actions:
                await update.effective_message.reply_text(
                    "🔍 **I detected potential actions in this image:**",
                    parse_mode=ParseMode.MARKDOWN
                )
                
                for action in actions:
                    confirmation_text = self.action_extractor.format_for_confirmation(action)
                    await update.effective_message.reply_text(
                        confirmation_text,
                        parse_mode=ParseMode.MARKDOWN
                    )
            
        except Exception as e:
            logger.error(f"Error handling photo: {e}")
            await update.effective_message.reply_text(
                "Sorry, I couldn't process the image. Please try again."
            )