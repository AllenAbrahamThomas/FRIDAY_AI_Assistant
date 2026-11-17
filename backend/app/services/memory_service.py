import datetime
from contextlib import contextmanager
import re
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from app.config import settings


class DuplicateMemoryError(ValueError):
    pass


class MemoryService:
    CATEGORIES = {"preference", "project", "task", "research"}

    def __init__(self, database_path: Optional[Path] = None):
        self.database_path = Path(database_path or settings.MEMORY_DB_PATH).expanduser()
        if not self.database_path.is_absolute():
            repository_root = Path(__file__).resolve().parents[3]
            self.database_path = repository_root / self.database_path

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(self.database_path), timeout=5)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    memory_enabled INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS conversations (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL REFERENCES conversations(session_id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK (role IN ('user', 'friday', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS memories (
                    memory_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    category TEXT NOT NULL CHECK (category IN ('preference', 'project', 'task', 'research')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_conversations_user_updated
                    ON conversations(user_id, updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_messages_session
                    ON messages(session_id, message_id);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_memories_user_content
                    ON memories(user_id, lower(content));
                """
            )
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _now() -> str:
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

    def _ensure_user(self, connection: sqlite3.Connection, user_id: str) -> None:
        connection.execute(
            "INSERT OR IGNORE INTO users (user_id, created_at) VALUES (?, ?)",
            (user_id, self._now())
        )

    def get_preferences(self, user_id: str) -> Dict[str, Any]:
        with self._connection() as connection:
            self._ensure_user(connection, user_id)
            row = connection.execute(
                "SELECT memory_enabled FROM users WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            return {"memory_enabled": bool(row["memory_enabled"])}

    def set_memory_enabled(self, user_id: str, enabled: bool) -> Dict[str, Any]:
        with self._connection() as connection:
            self._ensure_user(connection, user_id)
            connection.execute(
                "UPDATE users SET memory_enabled = ? WHERE user_id = ?",
                (int(enabled), user_id)
            )
        return {"memory_enabled": enabled}

    def create_session(self, user_id: str, title: str) -> Dict[str, Any]:
        session_id = str(uuid.uuid4())
        now = self._now()
        clean_title = " ".join(title.split())[:120] or "New conversation"
        with self._connection() as connection:
            self._ensure_user(connection, user_id)
            connection.execute(
                """
                INSERT INTO conversations (session_id, user_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, user_id, clean_title, now, now)
            )
        return {
            "session_id": session_id,
            "title": clean_title,
            "created_at": now,
            "updated_at": now
        }

    def get_session(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT session_id, title, created_at, updated_at
                FROM conversations WHERE user_id = ? AND session_id = ?
                """,
                (user_id, session_id)
            ).fetchone()
        return dict(row) if row else None

    def list_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT c.session_id, c.title, c.created_at, c.updated_at, COUNT(m.message_id) AS message_count
                FROM conversations AS c
                LEFT JOIN messages AS m ON m.session_id = c.session_id
                WHERE c.user_id = ?
                GROUP BY c.session_id
                ORDER BY c.updated_at DESC
                """,
                (user_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def get_messages(
        self,
        user_id: str,
        session_id: str,
        limit: int = 20
    ) -> List[Dict[str, str]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT m.role, m.content, m.created_at
                FROM messages AS m
                JOIN conversations AS c ON c.session_id = m.session_id
                WHERE c.user_id = ? AND c.session_id = ?
                ORDER BY m.message_id DESC
                LIMIT ?
                """,
                (user_id, session_id, limit)
            ).fetchall()
        return [
            {"role": row["role"], "content": row["content"], "created_at": row["created_at"]}
            for row in reversed(rows)
        ]

    def append_turn(self, user_id: str, session_id: str, prompt: str, response: str) -> None:
        now = self._now()
        with self._connection() as connection:
            session = connection.execute(
                "SELECT 1 FROM conversations WHERE user_id = ? AND session_id = ?",
                (user_id, session_id)
            ).fetchone()
            if not session:
                raise LookupError("Conversation session was not found for this user")
            connection.executemany(
                """
                INSERT INTO messages (session_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (session_id, "user", prompt, now),
                    (session_id, "friday", response, now)
                ]
            )
            connection.execute(
                "UPDATE conversations SET updated_at = ? WHERE session_id = ?",
                (now, session_id)
            )

    def delete_session(self, user_id: str, session_id: str) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM conversations WHERE user_id = ? AND session_id = ?",
                (user_id, session_id)
            )
            return cursor.rowcount > 0

    def create_memory(self, user_id: str, category: str, content: str) -> Dict[str, Any]:
        clean_content = " ".join(content.split())
        if category not in self.CATEGORIES:
            raise ValueError("Unsupported memory category")
        if not clean_content:
            raise ValueError("Memory content cannot be empty")
        if len(clean_content) > 2000:
            raise ValueError("Memory content cannot exceed 2000 characters")

        now = self._now()
        try:
            with self._connection() as connection:
                self._ensure_user(connection, user_id)
                cursor = connection.execute(
                    """
                    INSERT INTO memories (user_id, category, content, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (user_id, category, clean_content, now, now)
                )
                memory_id = cursor.lastrowid
        except sqlite3.IntegrityError as exc:
            if "idx_memories_user_content" in str(exc) or "UNIQUE constraint failed" in str(exc):
                raise DuplicateMemoryError("This memory already exists") from exc
            raise
        return {
            "memory_id": memory_id,
            "category": category,
            "content": clean_content,
            "created_at": now,
            "updated_at": now
        }

    def list_memories(self, user_id: str) -> List[Dict[str, Any]]:
        with self._connection() as connection:
            self._ensure_user(connection, user_id)
            rows = connection.execute(
                """
                SELECT memory_id, category, content, created_at, updated_at
                FROM memories WHERE user_id = ?
                ORDER BY updated_at DESC, memory_id DESC
                """,
                (user_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_memory(self, user_id: str, memory_id: int) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM memories WHERE user_id = ? AND memory_id = ?",
                (user_id, memory_id)
            )
            return cursor.rowcount > 0

    def retrieve_relevant_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        query_terms = set(re.findall(r"[a-z0-9]{3,}", query.casefold()))
        memories = self.list_memories(user_id)
        scored = []
        for memory in memories:
            memory_terms = set(re.findall(r"[a-z0-9]{3,}", memory["content"].casefold()))
            score = len(query_terms & memory_terms)
            if memory["category"] == "preference":
                score = max(score, 1)
            if score:
                scored.append((score, memory))
        scored.sort(key=lambda result: (result[0], result[1]["updated_at"]), reverse=True)
        return [memory for _, memory in scored[:limit]]

    def build_memory_context(self, user_id: str, query: str) -> str:
        memories = self.retrieve_relevant_memories(user_id, query)
        return "\n".join(
            f"- [{memory['category']}] {memory['content']}"
            for memory in memories
        )


memory_service = MemoryService()
