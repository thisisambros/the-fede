"""Main entry point for The Fede bot."""

import asyncio
import logging
import signal
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.bot.core import FedeBot
from src.utils.config import load_settings


def setup_logging(level: str = "INFO", debug: bool = False) -> None:
    """Configure logging for the application.
    
    Args:
        level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        debug: Whether to enable debug mode (overrides level)
    """
    log_level = logging.DEBUG if debug else getattr(logging, level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Reduce noise from external libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)


async def run_bot() -> None:
    """Run the bot with proper initialization and error handling.
    
    Loads configuration, sets up logging, initializes the bot,
    and handles graceful shutdown on interrupt signals.
    """
    # Load environment variables
    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(env_path)
    else:
        logging.warning("No .env file found. Using environment variables.")
    
    # Load settings
    try:
        settings = load_settings()
    except Exception as e:
        logging.error(f"Failed to load settings: {e}")
        logging.error("Please check your .env file and ensure all required variables are set.")
        sys.exit(1)
    
    # Setup logging
    setup_logging(settings.log_level, settings.debug)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting The Fede bot...")
    
    # Create and initialize a bot
    bot = FedeBot(settings)
    
    try:
        await bot.initialize()
        await bot.start()
        
        logger.info("Bot is running. Press Ctrl+C to stop.")
        
        # Keep the bot running
        stop_event = asyncio.Event()
        
        def signal_handler(signum, frame):
            logger.info("Received interrupt signal. Shutting down...")
            stop_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        await stop_event.wait()
        
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)
    finally:
        logger.info("Stopping bot...")
        await bot.stop()
        logger.info("Bot stopped.")


def main() -> None:
    """Main entry point for the application.
    
    Handles the async event loop and top-level exception handling.
    """
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()