import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from app.config import settings
from app.schemas.execution import ExecutionTrace


_SENSITIVE_KEY = re.compile(
    r"\b(?:password|passphrase|secret(?:[_-]?key)?|client[_-]?secret|private[_-]?key|"
    r"api[_-]?key|access[_-]?(?:token|key)|refresh[_-]?token|authorization|"
    r"credential|cookie|token)\b",
    re.IGNORECASE
)
_SENSITIVE_ASSIGNMENT = re.compile(
    r"(?i)\b(password|passphrase|secret(?:[_-]?key)?|client[_-]?secret|private[_-]?key|"
    r"api[_-]?key|access[_-]?(?:token|key)|refresh[_-]?token|authorization|"
    r"credential|cookie|token)\b"
    r"['\"]?\s*[:=]\s*['\"]?[^'\"\s,;]+['\"]?"
)
_BEARER_TOKEN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*")
_COMMON_SECRET = re.compile(r"\b(?:sk|ghp|github_pat)-[A-Za-z0-9_-]{20,}\b")


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if _SENSITIVE_KEY.search(str(key)) else _sanitize(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, str):
        sanitized = _BEARER_TOKEN.sub("Bearer [REDACTED]", value)
        sanitized = _SENSITIVE_ASSIGNMENT.sub(r"\1=[REDACTED]", sanitized)
        sanitized = _COMMON_SECRET.sub("[REDACTED]", sanitized)
        return sanitized[:4000]
    return value


class ExecutionHistoryService:
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
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS execution_history_settings (
                    user_id TEXT PRIMARY KEY,
                    enabled INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS execution_history (
                    trace_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    agent_used TEXT,
                    total_duration_seconds REAL NOT NULL,
                    model_used TEXT NOT NULL,
                    model_latency_seconds REAL,
                    token_count INTEGER,
                    trace_json TEXT NOT NULL,
                    feedback TEXT CHECK (feedback IN ('positive', 'negative') OR feedback IS NULL)
                );
                CREATE INDEX IF NOT EXISTS idx_execution_history_user_created
                    ON execution_history(user_id, created_at DESC);
                """
            )
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get_settings(self, user_id: str) -> Dict[str, bool]:
        with self._connection() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO execution_history_settings (user_id) VALUES (?)",
                (user_id,)
            )
            row = connection.execute(
                "SELECT enabled FROM execution_history_settings WHERE user_id = ?",
                (user_id,)
            ).fetchone()
        return {"enabled": bool(row["enabled"])}

    def set_enabled(self, user_id: str, enabled: bool) -> Dict[str, bool]:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO execution_history_settings (user_id, enabled)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET enabled = excluded.enabled
                """,
                (user_id, int(enabled))
            )
        return {"enabled": enabled}

    def save_trace(self, user_id: str, trace: ExecutionTrace) -> bool:
        trace_data = _sanitize(trace.model_dump(mode="json"))
        with self._connection() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO execution_history_settings (user_id) VALUES (?)",
                (user_id,)
            )
            enabled = connection.execute(
                "SELECT enabled FROM execution_history_settings WHERE user_id = ?",
                (user_id,)
            ).fetchone()["enabled"]
            if not enabled:
                return False
            connection.execute(
                """
                INSERT INTO execution_history (
                    trace_id, user_id, created_at, intent, agent_used,
                    total_duration_seconds, model_used, model_latency_seconds,
                    token_count, trace_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trace.trace_id,
                    user_id,
                    trace.created_at,
                    trace.intent.intent,
                    trace.agent_used,
                    trace.total_duration_seconds,
                    trace.model_used,
                    trace.model_latency_seconds,
                    trace.token_count,
                    json.dumps(trace_data, ensure_ascii=False)
                )
            )
        return True

    def list_history(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        bounded_limit = max(1, min(limit, 100))
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT trace_id, created_at, intent, agent_used, total_duration_seconds,
                       model_used, model_latency_seconds, token_count, trace_json, feedback
                FROM execution_history
                WHERE user_id = ?
                ORDER BY created_at DESC, rowid DESC
                LIMIT ?
                """,
                (user_id, bounded_limit)
            ).fetchall()
        return [
            {
                "trace_id": row["trace_id"],
                "created_at": row["created_at"],
                "intent": row["intent"],
                "agent_used": row["agent_used"],
                "total_duration_seconds": row["total_duration_seconds"],
                "model_used": row["model_used"],
                "model_latency_seconds": row["model_latency_seconds"],
                "token_count": row["token_count"],
                "feedback": row["feedback"],
                "trace": json.loads(row["trace_json"])
            }
            for row in rows
        ]

    def get_trace(self, user_id: str, trace_id: str) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT trace_id, created_at, intent, agent_used, total_duration_seconds,
                       model_used, model_latency_seconds, token_count, trace_json, feedback
                FROM execution_history
                WHERE user_id = ? AND trace_id = ?
                """,
                (user_id, trace_id)
            ).fetchone()
        if not row:
            return None
        return {
            "trace_id": row["trace_id"],
            "created_at": row["created_at"],
            "intent": row["intent"],
            "agent_used": row["agent_used"],
            "total_duration_seconds": row["total_duration_seconds"],
            "model_used": row["model_used"],
            "model_latency_seconds": row["model_latency_seconds"],
            "token_count": row["token_count"],
            "feedback": row["feedback"],
            "trace": json.loads(row["trace_json"])
        }

    def set_feedback(self, user_id: str, trace_id: str, rating: str) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE execution_history SET feedback = ?
                WHERE user_id = ? AND trace_id = ?
                """,
                (rating, user_id, trace_id)
            )
            return cursor.rowcount > 0

    def delete_trace(self, user_id: str, trace_id: str) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM execution_history WHERE user_id = ? AND trace_id = ?",
                (user_id, trace_id)
            )
            return cursor.rowcount > 0

    def clear_history(self, user_id: str) -> int:
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM execution_history WHERE user_id = ?",
                (user_id,)
            )
            return cursor.rowcount


execution_history_service = ExecutionHistoryService()
