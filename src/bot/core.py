"""Core Telegram bot implementation."""

import logging
from typing import Optional

from telegram.ext import Application as TelegramApplication

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from ..claude.client import ClaudeClient
from ..claude.session import SessionManager
from ..utils.config import Settings
from .handlers import MessageHandlers

logger = logging.getLogger(__name__)


class FedeBot:
    """Main Telegram bot class."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the Fede bot with configuration settings.
        
        Args:
            settings: Application configuration settings
        """
        self.settings = settings
        self.app: Optional[TelegramApplication] = None
        self.claude_client = ClaudeClient(settings)
        self.session_manager = SessionManager(
            settings.database_path,
            settings.session_timeout_hours
        )
        self.handlers = MessageHandlers(
            self.claude_client,
            self.session_manager,
            settings
        )

    async def initialize(self) -> None:
        """Initialize bot components including database and handlers.
        
        Sets up the database connection, creates the Telegram application,
        registers message handlers, and configures error handling.
        """
        logger.info("Initializing Fede bot...")
        
        # Initialize database
        await self.session_manager.initialize()
        
        # Create Telegram application
        self.app = (
            Application.builder()
            .token(self.settings.telegram_bot_token)
            .build()
        )
        
        # Register handlers
        self._register_handlers()
        
        # Set up error handler
        self.app.add_error_handler(self._error_handler)
        
        logger.info("Bot initialization complete")

    def _register_handlers(self) -> None:
        """Register all message handlers for the bot.
        
        Registers command handlers for /start, /help, /new, /end, /status, /calendar,
        as well as handlers for text messages and photos.
        """
        # Command handlers
        self.app.add_handler(CommandHandler("start", self.handlers.handle_start))
        self.app.add_handler(CommandHandler("help", self.handlers.handle_help))
        self.app.add_handler(CommandHandler("new", self.handlers.handle_new_session))
        self.app.add_handler(CommandHandler("end", self.handlers.handle_end_session))
        self.app.add_handler(CommandHandler("status", self.handlers.handle_status))
        self.app.add_handler(CommandHandler("calendar", self.handlers.handle_calendar))
        
        # Text message handler
        self.app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.handlers.handle_text_message
            )
        )
        
        # Photo handler (for screenshots)
        self.app.add_handler(
            MessageHandler(
                filters.PHOTO,
                self.handlers.handle_photo
            )
        )

    async def _error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors that occur during message processing.
        
        Args:
            update: The Telegram update that caused the error
            context: The error context containing exception details
        """
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "Sorry, an error occurred while processing your request. Please try again."
            )

    async def start(self) -> None:
        """Start the bot and begin polling for messages.
        
        Initializes the Telegram application and starts the update polling loop.
        """
        logger.info("Starting Fede bot...")
        
        # Initialize the application
        await self.app.initialize()
        await self.app.start()
        
        # Start polling
        logger.info(f"Bot started. Authorized user: {self.settings.telegram_user_id}")
        await self.app.updater.start_polling()

    async def stop(self) -> None:
        """Stop the bot gracefully.
        
        Stops the update polling, shuts down the application, and cleans up resources.
        """
        logger.info("Stopping Fede bot...")
        
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
        
        logger.info("Bot stopped")