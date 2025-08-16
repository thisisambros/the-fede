"""Configuration management using Pydantic Settings."""

from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Telegram settings
    telegram_bot_token: str = Field(..., description="Telegram bot token from BotFather")
    telegram_user_id: int = Field(..., description="Authorized Telegram user ID")

    # Claude settings
    use_claude_sdk: bool = Field(
        default=False,
        description="Use Claude Code SDK for enhanced capabilities (images, tools)"
    )
    anthropic_api_key: str = Field(..., description="Anthropic API key")
    claude_model: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Claude model to use",
    )
    claude_max_tokens: int = Field(
        default=4096,
        description="Maximum tokens per Claude response",
    )

    # MCP Server integrations
    mcp_gmail_enabled: bool = Field(default=False, description="Enable Gmail MCP server")
    mcp_calendar_enabled: bool = Field(default=False, description="Enable Google Calendar MCP server")
    google_oauth_credentials: Optional[str] = Field(
        default=None, description="Path to Google OAuth credentials JSON file"
    )
    
    calendar_enabled: bool = Field(default=False, description="Enable Calendar integration (deprecated)")
    calendar_credentials_path: Optional[str] = Field(
        default=None, description="Path to Calendar credentials (deprecated)"
    )
    
    todo_enabled: bool = Field(default=False, description="Enable Todo integration")
    todo_api_url: Optional[str] = Field(default=None, description="Todo API URL")
    todo_api_key: Optional[str] = Field(default=None, description="Todo API key")

    # Storage settings
    database_path: Path = Field(
        default=Path("./data/fede.db"),
        description="SQLite database path",
    )
    session_timeout_hours: int = Field(
        default=0,
        description="Session timeout in hours (0 = no timeout)",
    )

    # Behavior settings
    require_explicit_confirmation: bool = Field(
        default=True,
        description="Require explicit confirmation before actions",
    )
    enable_learning_mode: bool = Field(
        default=True,
        description="Enable learning user patterns",
    )
    learning_threshold: int = Field(
        default=3,
        description="Pattern occurrences before suggesting as default",
    )

    # Development settings
    log_level: str = Field(default="INFO", description="Logging level")
    debug: bool = Field(default=False, description="Enable debug mode")

    @field_validator("database_path", mode="before")
    def ensure_database_dir(cls, v):
        """Ensure database directory exists."""
        path = Path(v)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @field_validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
        return v.upper()


def load_settings() -> Settings:
    """Load and validate settings from environment."""
    return Settings()