# The Fede - Personal AI Assistant Bot

A sophisticated Telegram bot that leverages Claude Code SDK to provide a personal AI assistant with advanced capabilities including image analysis, task management, and MCP server integrations.

## Features

### Current
- ✅ **AI-Powered Conversations**: Full Claude Code SDK integration with tool support
- ✅ **Image Analysis**: Analyze screenshots and images with vision capabilities
- ✅ **Persistent Sessions**: SQLite-based conversation history
- ✅ **Smart Action Extraction**: Automatically identifies actionable items from conversations
- ✅ **Pattern Learning**: Learns user patterns and suggests defaults (with confirmation)
- ✅ **Single-User Security**: Restricted to authorized Telegram user ID

### Planned
- 📧 Gmail integration via MCP server
- 📅 Google Calendar management
- ✅ Custom todo list integration
- 🔄 Enhanced action staging and confirmation workflow

## Prerequisites

- Python 3.10 or higher
- Poetry for dependency management
- Telegram Bot Token (from @BotFather)
- Anthropic API Key

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/the-fede.git
   cd the-fede
   ```

2. **Install dependencies**
   ```bash
   poetry install
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your credentials:
   - `TELEGRAM_BOT_TOKEN`: Your bot token from @BotFather
   - `TELEGRAM_USER_ID`: Your Telegram user ID (get from @userinfobot)
   - `ANTHROPIC_API_KEY`: Your Anthropic API key

4. **Run the bot**
   ```bash
   poetry run python main.py
   ```

## Usage

### Available Commands

- `/start` - Initialize the bot
- `/help` - Show available commands
- `/new` - Start a new conversation session
- `/end` - End the current session
- `/status` - Show session status

### Sending Images

Simply send an image to the bot and it will analyze it using Claude's vision capabilities. The bot can:
- Extract text from screenshots
- Identify participants in conversations
- Extract actionable items (calendar events, tasks, emails)
- Analyze general image content

### Interaction Style

The bot is designed to be extremely careful about taking actions:
- Always asks for explicit confirmation before any action
- Never assumes default values
- Requests all parameters explicitly
- Learns patterns but asks before applying them

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | Required |
| `TELEGRAM_USER_ID` | Authorized user's Telegram ID | Required |
| `ANTHROPIC_API_KEY` | Anthropic API key | Required |
| `USE_CLAUDE_SDK` | Use Claude Code SDK (vs API) | true |
| `CLAUDE_MODEL` | Claude model to use | claude-3-5-sonnet-20241022 |
| `CLAUDE_MAX_TOKENS` | Max tokens per response | 4096 |
| `DATABASE_PATH` | SQLite database location | ./data/fede.db |
| `SESSION_TIMEOUT_HOURS` | Session timeout (0 = no timeout) | 0 |
| `REQUIRE_EXPLICIT_CONFIRMATION` | Require confirmation for actions | true |
| `ENABLE_LEARNING_MODE` | Enable pattern learning | true |
| `LEARNING_THRESHOLD` | Pattern occurrences before suggestion | 3 |
| `LOG_LEVEL` | Logging level | INFO |
| `DEBUG` | Enable debug mode | false |

### MCP Server Integration (Future)

To enable Gmail MCP server (when ready):

1. Install the Gmail MCP server:
   ```bash
   npx -y @smithery/cli install @gongrzhe/server-gmail-autoauth-mcp --client claude
   ```

2. Set `MCP_GMAIL_ENABLED=true` in your `.env` file

3. Configure Gmail OAuth credentials

## Project Structure

```
the-fede/
├── src/
│   ├── bot/           # Telegram bot handlers
│   │   ├── core.py    # Main bot class
│   │   └── handlers.py # Message handlers
│   ├── claude/        # Claude SDK integration
│   │   ├── client.py  # Claude Code SDK client
│   │   ├── session.py # Session management
│   │   ├── personality.py # Bot personality
│   │   └── prompts.py # System prompts
│   ├── actions/       # Action extraction logic
│   │   └── extractor.py # Extract actionable items
│   ├── utils/         # Utilities and configuration
│   │   └── config.py  # Settings management
│   └── __init__.py
├── data/              # SQLite database (created on first run)
├── main.py            # Entry point
├── pyproject.toml     # Poetry dependencies
├── .env               # Environment configuration
├── .env.example       # Example configuration
└── README.md
```

## Development

### Running Tests

```bash
poetry run pytest
```

### Code Quality

```bash
# Format code
poetry run black .

# Lint
poetry run ruff .

# Type checking
poetry run mypy .
```

### Testing the Bot

1. Start the bot with `poetry run python main.py`
2. Open Telegram and search for your bot
3. Send `/start` to initialize
4. Send any text message to interact with Claude
5. Send an image to test vision capabilities

## Security Considerations

- The bot is restricted to a single authorized user ID
- API keys should never be committed to version control
- Database contains conversation history - handle with care
- MCP servers run with restricted permissions
- All actions require explicit user confirmation

## Troubleshooting

### Bot not responding
- Check that only one instance is running
- Verify your Telegram user ID is correct
- Check logs for error messages
- Ensure bot token is valid

### Image analysis not working
- Ensure the image is in a supported format (JPEG, PNG)
- Check that the bot has sufficient permissions
- Verify Claude SDK is properly initialized
- Check available disk space for temp files

### Claude API errors
- Verify your Anthropic API key is correct
- Check API rate limits and quota
- Review logs for detailed error messages

### Database issues
- The database is created automatically in `./data/fede.db`
- Delete the database file to reset all sessions
- Check disk space and write permissions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built with [Claude Code SDK](https://github.com/anthropics/claude-code-sdk)
- Uses [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- MCP integration via [Smithery](https://smithery.ai)

## Roadmap

- [x] Phase 1: Core bot with Claude integration
- [x] Phase 2: Image analysis and vision capabilities
- [x] Phase 3: Session management and persistence
- [ ] Phase 4: MCP server integration (Gmail, Calendar, Todo)
- [ ] Phase 5: Enhanced permission workflow
- [ ] Phase 6: Advanced pattern learning
- [ ] Phase 7: Multi-user support (optional)