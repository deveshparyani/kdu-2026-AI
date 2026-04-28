"""SQLite chat history database."""

import json
import sqlite3
from datetime import datetime
from typing import Optional


class ChatDatabase:
    """SQLite database for chat history."""
    
    def __init__(self, db_path: str):
        """Initialize database connection."""
        self.db_path = db_path
        self._init_schema()
    
    def _init_schema(self) -> None:
        """Create database schema if not exists."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                current_file_id TEXT
            )
        """)
        
        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def create_conversation(self, conversation_id: str) -> str:
        """Create a new conversation."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO conversations (id, created_at) VALUES (?, ?)",
            (conversation_id, datetime.utcnow().isoformat())
        )
        
        conn.commit()
        conn.close()
        return conversation_id
    
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> int:
        """Add a message to conversation."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor.execute(
            """INSERT INTO messages 
               (conversation_id, role, content, metadata, created_at) 
               VALUES (?, ?, ?, ?, ?)""",
            (conversation_id, role, content, metadata_json, datetime.utcnow().isoformat())
        )
        
        message_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return message_id
    
    def get_conversation_history(
        self,
        conversation_id: str,
        limit: Optional[int] = None
    ) -> list[dict]:
        """Get conversation message history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
            SELECT role, content, metadata, created_at 
            FROM messages 
            WHERE conversation_id = ? 
            ORDER BY created_at ASC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query, (conversation_id,))
        rows = cursor.fetchall()
        conn.close()
        
        messages = []
        for row in rows:
            messages.append({
                "role": row[0],
                "content": row[1],
                "metadata": json.loads(row[2]) if row[2] else None,
                "created_at": row[3]
            })
        
        return messages
    
    def set_current_file(self, conversation_id: str, file_id: str) -> None:
        """Set the current file for a conversation."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE conversations SET current_file_id = ? WHERE id = ?",
            (file_id, conversation_id)
        )
        
        conn.commit()
        conn.close()
    
    def get_current_file(self, conversation_id: str) -> Optional[str]:
        """Get the current file for a conversation."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT current_file_id FROM conversations WHERE id = ?",
            (conversation_id,)
        )
        
        row = cursor.fetchone()
        conn.close()
        
        return row[0] if row else None
