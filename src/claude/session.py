"""Session management for conversation persistence."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiosqlite

logger = logging.getLogger(__name__)


class SessionManager:
    """Manage conversation sessions with persistence."""

    def __init__(self, db_path: Union[Path, str], timeout_hours: int = 0) -> None:
        """Initialize session manager with database path and timeout.
        
        Args:
            db_path: Path to the SQLite database file
            timeout_hours: Hours before a session times out (0 = no timeout)
        """
        self.db_path = Path(db_path) if isinstance(db_path, str) else db_path
        self.timeout_hours = timeout_hours
        self.current_session: Optional[Dict[str, Any]] = None

    async def initialize(self) -> None:
        """Initialize the database schema.
        
        Creates tables for sessions, messages, and user patterns if they don't exist.
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    context TEXT
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (id)
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    pattern_key TEXT NOT NULL,
                    pattern_value TEXT NOT NULL,
                    occurrence_count INTEGER DEFAULT 1,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_confirmed_default BOOLEAN DEFAULT FALSE,
                    UNIQUE(user_id, pattern_key, pattern_value)
                )
            """)
            
            await db.commit()

    async def get_or_create_session(self, user_id: int) -> int:
        """Get active session or create a new one.
        
        Args:
            user_id: The Telegram user ID
            
        Returns:
            The session ID (either existing or newly created)
        """
        async with aiosqlite.connect(self.db_path) as db:
            # Check for active session
            if self.timeout_hours > 0:
                timeout_threshold = datetime.now() - timedelta(hours=self.timeout_hours)
                await db.execute(
                    "UPDATE sessions SET is_active = FALSE WHERE user_id = ? AND updated_at < ?",
                    (user_id, timeout_threshold)
                )
                await db.commit()

            cursor = await db.execute(
                "SELECT id, context FROM sessions WHERE user_id = ? AND is_active = TRUE ORDER BY updated_at DESC LIMIT 1",
                (user_id,)
            )
            row = await cursor.fetchone()

            if row:
                session_id = row[0]
                context = json.loads(row[1]) if row[1] else {}
                logger.info(f"Found active session {session_id} for user {user_id}")
            else:
                # Create new session
                cursor = await db.execute(
                    "INSERT INTO sessions (user_id, context) VALUES (?, ?)",
                    (user_id, json.dumps({}))
                )
                session_id = cursor.lastrowid
                context = {}
                await db.commit()
                logger.info(f"Created new session {session_id} for user {user_id}")

            self.current_session = {"id": session_id, "user_id": user_id, "context": context}
            return session_id

    async def add_message(self, session_id: int, role: str, content: str) -> None:
        """Add a message to the session history.
        
        Args:
            session_id: The session to add the message to
            role: The role of the message sender ('user' or 'assistant')
            content: The message content
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, role, content)
            )
            await db.execute(
                "UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (session_id,)
            )
            await db.commit()

    async def get_messages(self, session_id: int, limit: int = 20) -> List[Dict[str, str]]:
        """Get recent messages from a session.
        
        Args:
            session_id: The session to retrieve messages from
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of message dictionaries with 'role' and 'content' keys
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT role, content FROM messages WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
                (session_id, limit)
            )
            rows = await cursor.fetchall()
            
            # Reverse to get chronological order
            messages = [{"role": row[0], "content": row[1]} for row in reversed(rows)]
            return messages

    async def update_context(self, session_id: int, context: Dict[str, Any]) -> None:
        """Update session context with additional information.
        
        Args:
            session_id: The session to update
            context: Dictionary of context information to store
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE sessions SET context = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (json.dumps(context), session_id)
            )
            await db.commit()
            
            if self.current_session and self.current_session["id"] == session_id:
                self.current_session["context"] = context

    async def end_session(self, session_id: int) -> None:
        """End a conversation session.
        
        Args:
            session_id: The session to end
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE sessions SET is_active = FALSE WHERE id = ?",
                (session_id,)
            )
            await db.commit()
            
            if self.current_session and self.current_session["id"] == session_id:
                self.current_session = None

    async def track_pattern(self, user_id: int, pattern_key: str, pattern_value: str) -> int:
        """Track a user behavior pattern for learning.
        
        Args:
            user_id: The user ID to track patterns for
            pattern_key: The type of pattern (e.g., 'email_recipient')
            pattern_value: The value of the pattern
            
        Returns:
            The updated occurrence count for this pattern
        """
        async with aiosqlite.connect(self.db_path) as db:
            # Check if pattern exists
            cursor = await db.execute(
                "SELECT occurrence_count FROM user_patterns WHERE user_id = ? AND pattern_key = ? AND pattern_value = ?",
                (user_id, pattern_key, pattern_value)
            )
            row = await cursor.fetchone()
            
            if row:
                new_count = row[0] + 1
                await db.execute(
                    "UPDATE user_patterns SET occurrence_count = ?, last_seen = CURRENT_TIMESTAMP WHERE user_id = ? AND pattern_key = ? AND pattern_value = ?",
                    (new_count, user_id, pattern_key, pattern_value)
                )
            else:
                new_count = 1
                await db.execute(
                    "INSERT INTO user_patterns (user_id, pattern_key, pattern_value) VALUES (?, ?, ?)",
                    (user_id, pattern_key, pattern_value)
                )
            
            await db.commit()
            return new_count

    async def get_pattern_suggestions(self, user_id: int, pattern_key: str, threshold: int = 3) -> List[Dict[str, Any]]:
        """Get pattern suggestions that meet the occurrence threshold.
        
        Args:
            user_id: The user ID to get patterns for
            pattern_key: The type of pattern to retrieve
            threshold: Minimum occurrence count for suggestions
            
        Returns:
            List of pattern dictionaries with 'value', 'count', and 'is_default' keys
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT pattern_value, occurrence_count, is_confirmed_default FROM user_patterns WHERE user_id = ? AND pattern_key = ? AND occurrence_count >= ? ORDER BY occurrence_count DESC",
                (user_id, pattern_key, threshold)
            )
            rows = await cursor.fetchall()
            
            return [
                {
                    "value": row[0],
                    "count": row[1],
                    "is_default": row[2]
                }
                for row in rows
            ]

    async def confirm_pattern_default(self, user_id: int, pattern_key: str, pattern_value: str) -> None:
        """Mark a pattern as a confirmed default value.
        
        Args:
            user_id: The user ID
            pattern_key: The type of pattern
            pattern_value: The value to set as default
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE user_patterns SET is_confirmed_default = TRUE WHERE user_id = ? AND pattern_key = ? AND pattern_value = ?",
                (user_id, pattern_key, pattern_value)
            )
            await db.commit()