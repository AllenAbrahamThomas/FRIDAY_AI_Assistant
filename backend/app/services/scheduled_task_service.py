import datetime
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from app.config import settings


class ScheduledTaskService:
    MIN_INTERVAL_MINUTES = 15
    MAX_INTERVAL_MINUTES = 10080

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
                CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    task_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    interval_minutes INTEGER NOT NULL
                        CHECK (interval_minutes BETWEEN 15 AND 10080),
                    status TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'paused')),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    next_run_at TEXT NOT NULL,
                    last_run_at TEXT,
                    last_status TEXT
                        CHECK (last_status IN ('running', 'completed', 'failed', 'missed') OR last_status IS NULL)
                );
                CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_due
                    ON scheduled_tasks(status, next_run_at);
                CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_user
                    ON scheduled_tasks(user_id, created_at DESC);
                CREATE TABLE IF NOT EXISTS scheduled_task_runs (
                    run_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL REFERENCES scheduled_tasks(task_id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL,
                    status TEXT NOT NULL
                        CHECK (status IN ('running', 'completed', 'failed', 'missed')),
                    scheduled_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    response TEXT,
                    error TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_scheduled_task_runs_user
                    ON scheduled_task_runs(user_id, scheduled_at DESC);
                CREATE INDEX IF NOT EXISTS idx_scheduled_task_runs_task
                    ON scheduled_task_runs(task_id, scheduled_at DESC);
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
    def _now(value: Optional[datetime.datetime] = None) -> datetime.datetime:
        return value or datetime.datetime.now(datetime.timezone.utc)

    @staticmethod
    def _task(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "task_id": row["task_id"],
            "title": row["title"],
            "prompt": row["prompt"],
            "interval_minutes": row["interval_minutes"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "next_run_at": row["next_run_at"],
            "last_run_at": row["last_run_at"],
            "last_status": row["last_status"]
        }

    def create_task(
        self,
        user_id: str,
        title: str,
        prompt: str,
        interval_minutes: int,
        now: Optional[datetime.datetime] = None
    ) -> Dict[str, Any]:
        created_at = self._now(now)
        task_id = uuid.uuid4().hex
        next_run_at = created_at + datetime.timedelta(minutes=interval_minutes)
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO scheduled_tasks (
                    task_id, user_id, title, prompt, interval_minutes, status,
                    created_at, updated_at, next_run_at
                ) VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?)
                """,
                (
                    task_id,
                    user_id,
                    title.strip(),
                    prompt.strip(),
                    interval_minutes,
                    created_at.isoformat(),
                    created_at.isoformat(),
                    next_run_at.isoformat()
                )
            )
            row = connection.execute(
                "SELECT * FROM scheduled_tasks WHERE task_id = ? AND user_id = ?",
                (task_id, user_id)
            ).fetchone()
        return self._task(row)

    def list_tasks(self, user_id: str) -> List[Dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM scheduled_tasks
                WHERE user_id = ?
                ORDER BY CASE status WHEN 'active' THEN 0 ELSE 1 END, next_run_at, created_at DESC
                """,
                (user_id,)
            ).fetchall()
        return [self._task(row) for row in rows]

    def get_task(self, user_id: str, task_id: str) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM scheduled_tasks WHERE user_id = ? AND task_id = ?",
                (user_id, task_id)
            ).fetchone()
        return self._task(row) if row else None

    def set_status(
        self,
        user_id: str,
        task_id: str,
        status: str,
        now: Optional[datetime.datetime] = None
    ) -> Optional[Dict[str, Any]]:
        if status not in {"active", "paused"}:
            raise ValueError(f"Unsupported scheduled task status: {status}")
        updated_at = self._now(now)
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT interval_minutes FROM scheduled_tasks
                WHERE user_id = ? AND task_id = ?
                """,
                (user_id, task_id)
            ).fetchone()
            if not row:
                return None
            next_run_at = updated_at + datetime.timedelta(minutes=row["interval_minutes"])
            connection.execute(
                """
                UPDATE scheduled_tasks
                SET status = ?, updated_at = ?, next_run_at = ?
                WHERE user_id = ? AND task_id = ?
                """,
                (status, updated_at.isoformat(), next_run_at.isoformat(), user_id, task_id)
            )
            updated = connection.execute(
                "SELECT * FROM scheduled_tasks WHERE user_id = ? AND task_id = ?",
                (user_id, task_id)
            ).fetchone()
        return self._task(updated)

    def delete_task(self, user_id: str, task_id: str) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM scheduled_tasks WHERE user_id = ? AND task_id = ?",
                (user_id, task_id)
            )
        return cursor.rowcount > 0

    def list_runs(
        self,
        user_id: str,
        task_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        bounded_limit = max(1, min(limit, 100))
        with self._connection() as connection:
            if task_id:
                rows = connection.execute(
                    """
                    SELECT r.*, t.title AS task_title
                    FROM scheduled_task_runs r
                    JOIN scheduled_tasks t ON t.task_id = r.task_id
                    WHERE r.user_id = ? AND r.task_id = ?
                    ORDER BY r.scheduled_at DESC, r.rowid DESC
                    LIMIT ?
                    """,
                    (user_id, task_id, bounded_limit)
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT r.*, t.title AS task_title
                    FROM scheduled_task_runs r
                    JOIN scheduled_tasks t ON t.task_id = r.task_id
                    WHERE r.user_id = ?
                    ORDER BY r.scheduled_at DESC, r.rowid DESC
                    LIMIT ?
                    """,
                    (user_id, bounded_limit)
                ).fetchall()
        return [
            {
                "run_id": row["run_id"],
                "task_id": row["task_id"],
                "task_title": row["task_title"],
                "status": row["status"],
                "scheduled_at": row["scheduled_at"],
                "started_at": row["started_at"],
                "completed_at": row["completed_at"],
                "response": row["response"],
                "error": row["error"]
            }
            for row in rows
        ]

    def claim_due_tasks(
        self,
        now: Optional[datetime.datetime] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        current_time = self._now(now)
        current_iso = current_time.isoformat()
        claimed: List[Dict[str, Any]] = []
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                """
                SELECT * FROM scheduled_tasks
                WHERE status = 'active' AND next_run_at <= ?
                ORDER BY next_run_at
                LIMIT ?
                """,
                (current_iso, limit)
            ).fetchall()
            for row in rows:
                scheduled_at = datetime.datetime.fromisoformat(row["next_run_at"])
                interval = datetime.timedelta(minutes=row["interval_minutes"])
                next_run_at = (current_time + interval).isoformat()
                if current_time - scheduled_at > interval:
                    error = "Skipped because the task was overdue by more than one configured interval."
                    connection.execute(
                        """
                        INSERT INTO scheduled_task_runs (
                            run_id, task_id, user_id, status, scheduled_at, completed_at, error
                        ) VALUES (?, ?, ?, 'missed', ?, ?, ?)
                        """,
                        (
                            uuid.uuid4().hex,
                            row["task_id"],
                            row["user_id"],
                            row["next_run_at"],
                            current_iso,
                            error
                        )
                    )
                    connection.execute(
                        """
                        UPDATE scheduled_tasks
                        SET updated_at = ?, next_run_at = ?, last_run_at = ?, last_status = 'missed'
                        WHERE task_id = ?
                        """,
                        (current_iso, next_run_at, current_iso, row["task_id"])
                    )
                    continue

                run_id = uuid.uuid4().hex
                connection.execute(
                    """
                    INSERT INTO scheduled_task_runs (
                        run_id, task_id, user_id, status, scheduled_at, started_at
                    ) VALUES (?, ?, ?, 'running', ?, ?)
                    """,
                    (run_id, row["task_id"], row["user_id"], row["next_run_at"], current_iso)
                )
                connection.execute(
                    """
                    UPDATE scheduled_tasks
                    SET updated_at = ?, next_run_at = ?, last_run_at = ?, last_status = 'running'
                    WHERE task_id = ?
                    """,
                    (current_iso, next_run_at, current_iso, row["task_id"])
                )
                claimed.append({
                    "run_id": run_id,
                    "task_id": row["task_id"],
                    "user_id": row["user_id"],
                    "title": row["title"],
                    "prompt": row["prompt"]
                })
        return claimed

    def finish_run(
        self,
        run_id: str,
        status: str,
        response: Optional[str] = None,
        error: Optional[str] = None,
        now: Optional[datetime.datetime] = None
    ) -> bool:
        if status not in {"completed", "failed"}:
            raise ValueError(f"Unsupported scheduled task run status: {status}")
        completed_at = self._now(now).isoformat()
        bounded_response = response[:12000] if response else None
        bounded_error = error[:1000] if error else None
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT task_id, user_id FROM scheduled_task_runs
                WHERE run_id = ? AND status = 'running'
                """,
                (run_id,)
            ).fetchone()
            if not row:
                return False
            connection.execute(
                """
                UPDATE scheduled_task_runs
                SET status = ?, completed_at = ?, response = ?, error = ?
                WHERE run_id = ? AND status = 'running'
                """,
                (status, completed_at, bounded_response, bounded_error, run_id)
            )
            connection.execute(
                """
                UPDATE scheduled_tasks
                SET updated_at = ?, last_run_at = ?, last_status = ?
                WHERE task_id = ? AND user_id = ?
                """,
                (completed_at, completed_at, status, row["task_id"], row["user_id"])
            )
        return True

    def recover_interrupted_runs(
        self,
        now: Optional[datetime.datetime] = None
    ) -> int:
        recovered_at = self._now(now).isoformat()
        error = "Backend stopped before this run completed; it was not retried automatically."
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT run_id, task_id, user_id FROM scheduled_task_runs WHERE status = 'running'"
            ).fetchall()
            connection.execute(
                """
                UPDATE scheduled_task_runs
                SET status = 'failed', completed_at = ?, error = ?
                WHERE status = 'running'
                """,
                (recovered_at, error)
            )
            for row in rows:
                connection.execute(
                    """
                    UPDATE scheduled_tasks
                    SET updated_at = ?, last_run_at = ?, last_status = 'failed'
                    WHERE task_id = ? AND user_id = ?
                    """,
                    (recovered_at, recovered_at, row["task_id"], row["user_id"])
                )
        return len(rows)


scheduled_task_service = ScheduledTaskService()
