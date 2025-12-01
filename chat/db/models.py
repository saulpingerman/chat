"""
Database models for CHAT using SQLite.
Handles users, conversations, and messages.
"""
import sqlite3
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from contextlib import contextmanager
import hashlib
import os

from chat.config import DATABASE_PATH


@dataclass
class User:
    """User model."""
    id: str
    username: str
    email: str
    password_hash: str
    created_at: datetime
    total_input_tokens: int = 0
    total_output_tokens: int = 0


@dataclass
class Conversation:
    """Conversation model."""
    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    is_saved: bool = False
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class Message:
    """Message model."""
    id: str
    conversation_id: str
    role: str  # 'user' or 'assistant'
    content: str  # JSON string for complex content
    created_at: datetime
    input_tokens: int = 0
    output_tokens: int = 0


def get_db_path() -> str:
    """Get the database path, creating directory if needed."""
    return DATABASE_PATH


@contextmanager
def get_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    """Initialize the database with required tables."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_input_tokens INTEGER DEFAULT 0,
                total_output_tokens INTEGER DEFAULT 0
            )
        """)

        # Conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_saved INTEGER DEFAULT 0,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)

        # Indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_user_id
            ON conversations(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
            ON messages(conversation_id)
        """)


def hash_password(password: str) -> str:
    """Hash a password using SHA-256 with salt."""
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + ':' + key.hex()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    try:
        salt_hex, key_hex = password_hash.split(':')
        salt = bytes.fromhex(salt_hex)
        stored_key = bytes.fromhex(key_hex)
        new_key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return new_key == stored_key
    except (ValueError, AttributeError):
        return False


# =============================================================================
# User Operations
# =============================================================================

def create_user(username: str, email: str, password: str) -> Optional[User]:
    """Create a new user."""
    user_id = str(uuid.uuid4())
    password_hash = hash_password(password)
    now = datetime.now()

    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO users (id, username, email, password_hash, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, username.lower(), email.lower(), password_hash, now.isoformat())
            )
            # Return user object directly instead of querying (avoids transaction issues)
            return User(
                id=user_id,
                username=username.lower(),
                email=email.lower(),
                password_hash=password_hash,
                created_at=now,
                total_input_tokens=0,
                total_output_tokens=0
            )
        except sqlite3.IntegrityError:
            return None


def get_user_by_id(user_id: str) -> Optional[User]:
    """Get a user by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return User(
                id=row['id'],
                username=row['username'],
                email=row['email'],
                password_hash=row['password_hash'],
                created_at=datetime.fromisoformat(row['created_at']),
                total_input_tokens=row['total_input_tokens'],
                total_output_tokens=row['total_output_tokens']
            )
        return None


def get_user_by_username(username: str) -> Optional[User]:
    """Get a user by username."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username.lower(),))
        row = cursor.fetchone()
        if row:
            return User(
                id=row['id'],
                username=row['username'],
                email=row['email'],
                password_hash=row['password_hash'],
                created_at=datetime.fromisoformat(row['created_at']),
                total_input_tokens=row['total_input_tokens'],
                total_output_tokens=row['total_output_tokens']
            )
        return None


def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate a user by username and password."""
    user = get_user_by_username(username)
    if user and verify_password(password, user.password_hash):
        return user
    return None


def update_user_tokens(user_id: str, input_tokens: int, output_tokens: int):
    """Update a user's total token usage."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users
            SET total_input_tokens = total_input_tokens + ?,
                total_output_tokens = total_output_tokens + ?
            WHERE id = ?
            """,
            (input_tokens, output_tokens, user_id)
        )


# =============================================================================
# Conversation Operations
# =============================================================================

def create_conversation(user_id: str, title: str = "New Chat") -> Conversation:
    """Create a new conversation."""
    conv_id = str(uuid.uuid4())
    now = datetime.now()

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO conversations (id, user_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (conv_id, user_id, title, now.isoformat(), now.isoformat())
        )

    return Conversation(
        id=conv_id,
        user_id=user_id,
        title=title,
        created_at=now,
        updated_at=now,
        is_saved=False,
        input_tokens=0,
        output_tokens=0
    )


def get_conversation(conv_id: str) -> Optional[Conversation]:
    """Get a conversation by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,))
        row = cursor.fetchone()
        if row:
            return Conversation(
                id=row['id'],
                user_id=row['user_id'],
                title=row['title'],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at']),
                is_saved=bool(row['is_saved']),
                input_tokens=row['input_tokens'],
                output_tokens=row['output_tokens']
            )
        return None


def get_user_conversations(user_id: str, saved_only: bool = False) -> List[Conversation]:
    """Get all conversations for a user."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if saved_only:
            cursor.execute(
                """
                SELECT * FROM conversations
                WHERE user_id = ? AND is_saved = 1
                ORDER BY updated_at DESC
                """,
                (user_id,)
            )
        else:
            cursor.execute(
                """
                SELECT * FROM conversations
                WHERE user_id = ?
                ORDER BY updated_at DESC
                """,
                (user_id,)
            )

        conversations = []
        for row in cursor.fetchall():
            conversations.append(Conversation(
                id=row['id'],
                user_id=row['user_id'],
                title=row['title'],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at']),
                is_saved=bool(row['is_saved']),
                input_tokens=row['input_tokens'],
                output_tokens=row['output_tokens']
            ))
        return conversations


def update_conversation(
    conv_id: str,
    title: Optional[str] = None,
    is_saved: Optional[bool] = None,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None
):
    """Update a conversation."""
    updates = []
    params = []

    if title is not None:
        updates.append("title = ?")
        params.append(title)
    if is_saved is not None:
        updates.append("is_saved = ?")
        params.append(1 if is_saved else 0)
    if input_tokens is not None:
        updates.append("input_tokens = input_tokens + ?")
        params.append(input_tokens)
    if output_tokens is not None:
        updates.append("output_tokens = output_tokens + ?")
        params.append(output_tokens)

    updates.append("updated_at = ?")
    params.append(datetime.now().isoformat())
    params.append(conv_id)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE conversations SET {', '.join(updates)} WHERE id = ?",
            params
        )


def delete_conversation(conv_id: str):
    """Delete a conversation and its messages."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
        cursor.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))


# =============================================================================
# Message Operations
# =============================================================================

def add_message(
    conversation_id: str,
    role: str,
    content: Any,
    input_tokens: int = 0,
    output_tokens: int = 0
) -> Message:
    """Add a message to a conversation."""
    msg_id = str(uuid.uuid4())
    now = datetime.now()

    # Serialize content to JSON if it's not a string
    # Bedrock API expects {"text": "..."} without a "type" key
    if isinstance(content, str):
        content_json = json.dumps([{"text": content}])
    else:
        # Clean up any "type" keys that might be in the content
        if isinstance(content, list):
            cleaned_content = []
            for block in content:
                if isinstance(block, dict):
                    # Remove "type" key if present - Bedrock doesn't accept it
                    cleaned = {k: v for k, v in block.items() if k != "type"}
                    cleaned_content.append(cleaned)
                else:
                    cleaned_content.append(block)
            content_json = json.dumps(cleaned_content)
        else:
            content_json = json.dumps(content)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO messages (id, conversation_id, role, content, created_at, input_tokens, output_tokens)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (msg_id, conversation_id, role, content_json, now.isoformat(), input_tokens, output_tokens)
        )

    return Message(
        id=msg_id,
        conversation_id=conversation_id,
        role=role,
        content=content_json,
        created_at=now,
        input_tokens=input_tokens,
        output_tokens=output_tokens
    )


def get_conversation_messages(conversation_id: str) -> List[Message]:
    """Get all messages for a conversation."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
            """,
            (conversation_id,)
        )

        messages = []
        for row in cursor.fetchall():
            messages.append(Message(
                id=row['id'],
                conversation_id=row['conversation_id'],
                role=row['role'],
                content=row['content'],
                created_at=datetime.fromisoformat(row['created_at']),
                input_tokens=row['input_tokens'],
                output_tokens=row['output_tokens']
            ))
        return messages


def get_messages_for_api(conversation_id: str) -> List[Dict[str, Any]]:
    """Get messages formatted for the Bedrock API."""
    messages = get_conversation_messages(conversation_id)
    api_messages = []

    for msg in messages:
        content = json.loads(msg.content)
        api_messages.append({
            "role": msg.role,
            "content": content
        })

    return api_messages
