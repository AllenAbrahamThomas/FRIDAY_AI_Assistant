import asyncio
import datetime
import os
import sys
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.schemas.agent import AgentResponse
from app.services.scheduled_task_runner import ScheduledTaskRunner
from app.services.scheduled_task_service import ScheduledTaskService


def test_scheduled_tasks_are_user_scoped_and_can_pause_resume_delete(tmp_path):
    service = ScheduledTaskService(tmp_path / "scheduled.sqlite3")
    owner = str(uuid4())
    other_user = str(uuid4())
    now = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)
    task = service.create_task(owner, "Daily briefing", "Summarize today's news", 60, now)

    assert service.list_tasks(other_user) == []
    assert service.set_status(other_user, task["task_id"], "paused", now) is None
    assert service.set_status(owner, task["task_id"], "paused", now)["status"] == "paused"
    assert service.claim_due_tasks(now + datetime.timedelta(days=1)) == []

    resumed = service.set_status(
        owner,
        task["task_id"],
        "active",
        now + datetime.timedelta(hours=2)
    )
    assert resumed["status"] == "active"
    assert resumed["next_run_at"] == (now + datetime.timedelta(hours=3)).isoformat()
    assert service.delete_task(other_user, task["task_id"]) is False
    assert service.delete_task(owner, task["task_id"]) is True
    assert service.list_tasks(owner) == []


def test_due_task_runs_are_recorded_and_late_tasks_are_marked_missed(tmp_path):
    service = ScheduledTaskService(tmp_path / "scheduled.sqlite3")
    user_id = str(uuid4())
    created = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)
    task = service.create_task(user_id, "Hourly briefing", "Summarize headlines", 15, created)
    due_at = created + datetime.timedelta(minutes=15)

    claimed = service.claim_due_tasks(due_at)
    assert len(claimed) == 1
    assert claimed[0]["task_id"] == task["task_id"]
    assert service.finish_run(claimed[0]["run_id"], "completed", "Briefing ready", now=due_at)
    run = service.list_runs(user_id)[0]
    assert run["status"] == "completed"
    assert run["response"] == "Briefing ready"

    next_due = due_at + datetime.timedelta(minutes=15)
    late_now = next_due + datetime.timedelta(minutes=16)
    assert service.claim_due_tasks(late_now) == []
    missed_run = service.list_runs(user_id)[0]
    assert missed_run["status"] == "missed"
    assert "overdue" in missed_run["error"]


def test_interrupted_runs_are_marked_failed(tmp_path):
    service = ScheduledTaskService(tmp_path / "scheduled.sqlite3")
    user_id = str(uuid4())
    created = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)
    task = service.create_task(user_id, "Briefing", "Summarize news", 15, created)
    claimed = service.claim_due_tasks(created + datetime.timedelta(minutes=15))

    assert service.recover_interrupted_runs(created + datetime.timedelta(minutes=16)) == 1
    run = service.list_runs(user_id, task["task_id"])[0]
    assert run["status"] == "failed"
    assert "Backend stopped" in run["error"]


@pytest.mark.asyncio
async def test_runner_executes_due_tasks_and_records_response(tmp_path):
    service = ScheduledTaskService(tmp_path / "scheduled.sqlite3")
    user_id = str(uuid4())
    created = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=16)
    service.create_task(user_id, "Briefing", "Summarize current headlines", 15, created)
    completed = asyncio.Event()
    fake_response = AgentResponse(response="Scheduled briefing", error=None)
    runner = ScheduledTaskRunner(service=service, poll_interval_seconds=1)

    async def process_request(prompt):
        assert prompt == "Summarize current headlines"
        completed.set()
        return fake_response

    with patch("app.services.scheduled_task_runner.friday_orchestrator.process_request", new=process_request):
        runner_task = asyncio.create_task(runner.run_forever())
        await asyncio.wait_for(completed.wait(), timeout=2)
        for _ in range(50):
            runs = await asyncio.to_thread(service.list_runs, user_id)
            if runs and runs[0]["status"] == "completed":
                break
            await asyncio.sleep(0.01)
        runner_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await runner_task

    assert service.list_runs(user_id)[0]["response"] == "Scheduled briefing"
    assert service.list_runs(user_id)[0]["status"] == "completed"


def test_scheduled_task_api_requires_user_and_validates_interval(tmp_path, monkeypatch):
    from app.services.scheduled_task_service import scheduled_task_service

    monkeypatch.setattr(scheduled_task_service, "database_path", tmp_path / "api.sqlite3")
    with TestClient(app) as client:
        assert client.get("/api/scheduled-tasks").status_code == 401
        user_id = str(uuid4())
        headers = {"X-User-ID": user_id}
        invalid = client.post(
            "/api/scheduled-tasks",
            headers=headers,
            json={
                "title": "Briefing",
                "prompt": "Summarize headlines",
                "interval_minutes": 5
            }
        )
        assert invalid.status_code == 422

        created = client.post(
            "/api/scheduled-tasks",
            headers=headers,
            json={
                "title": "Briefing",
                "prompt": "Summarize headlines",
                "interval_minutes": 60
            }
        )
        assert created.status_code == 201
        task_id = created.json()["task"]["task_id"]
        assert client.post(f"/api/scheduled-tasks/{task_id}/pause", headers=headers).json()["task"]["status"] == "paused"
        assert client.post(f"/api/scheduled-tasks/{task_id}/resume", headers=headers).json()["task"]["status"] == "active"
        assert client.delete(f"/api/scheduled-tasks/{task_id}", headers=headers).json()["deleted"] is True
