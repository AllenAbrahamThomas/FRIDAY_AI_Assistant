import os
import sys
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.orchestrator import friday_orchestrator
from app.main import app
from app.schemas.agent import AgentResponse
from app.schemas.execution import ExecutionTrace, IntentResult, PlanStep, ExecutionPlan
from app.services.execution_history_service import execution_history_service
from app.services.memory_service import memory_service


client = TestClient(app)


def make_trace(trace_id=None):
    trace_id = trace_id or f"trc-{uuid4().hex[:8]}"
    step = PlanStep(
        step_number=1,
        description="Search the web",
        tool_name="web_search",
        tool_input={
            "query": "news",
            "api_key": "tool-secret",
            "client_secret": "client-secret"
        },
        status="completed",
        observation="Authorization: Bearer bearer-secret",
        duration_seconds=0.25
    )
    return ExecutionTrace(
        trace_id=trace_id,
        user_prompt="Search with api_key=prompt-secret",
        intent=IntentResult(intent="research", requires_tools=True),
        agent_used="research_agent",
        plan=ExecutionPlan(
            task_goal="Search safely",
            steps=[step]
        ),
        steps_executed=[step],
        total_duration_seconds=1.5,
        model_latency_seconds=1.0,
        token_count=32,
        model_used="llama3.2",
        warnings=[],
        created_at="2026-03-20T12:00:00+00:00"
    )


@pytest.fixture(autouse=True)
def isolated_history_database(tmp_path, monkeypatch):
    database_path = tmp_path / "history.sqlite3"
    monkeypatch.setattr(execution_history_service, "database_path", database_path)
    monkeypatch.setattr(memory_service, "database_path", database_path)
    return database_path


def test_execution_history_requires_separate_opt_in_and_is_user_scoped():
    user_a = str(uuid4())
    user_b = str(uuid4())
    trace = make_trace()

    assert execution_history_service.get_settings(user_a)["enabled"] is False
    assert execution_history_service.save_trace(user_a, trace) is False
    assert execution_history_service.list_history(user_a) == []

    execution_history_service.set_enabled(user_a, True)
    assert execution_history_service.get_settings(user_b)["enabled"] is False
    assert execution_history_service.save_trace(user_a, trace) is True
    assert execution_history_service.list_history(user_b) == []

    saved = execution_history_service.get_trace(user_a, trace.trace_id)
    assert saved is not None
    assert saved["token_count"] == 32
    assert saved["trace"]["user_prompt"] == "Search with api_key=[REDACTED]"
    step = saved["trace"]["steps_executed"][0]
    assert step["tool_input"]["api_key"] == "[REDACTED]"
    assert step["tool_input"]["client_secret"] == "[REDACTED]"
    assert "bearer-secret" not in step["observation"]
    assert "[REDACTED]" in step["observation"]

    assert execution_history_service.set_feedback(user_a, trace.trace_id, "positive") is True
    assert execution_history_service.get_trace(user_a, trace.trace_id)["feedback"] == "positive"
    assert execution_history_service.set_feedback(user_b, trace.trace_id, "negative") is False
    assert execution_history_service.delete_trace(user_b, trace.trace_id) is False
    assert execution_history_service.delete_trace(user_a, trace.trace_id) is True


def test_execution_history_api_supports_settings_feedback_and_deletion():
    user_id = str(uuid4())
    headers = {"X-User-ID": user_id}

    assert client.get("/api/history/settings").status_code == 401
    assert client.get("/api/history", headers=headers).json()["history"] == []

    enabled = client.put(
        "/api/history/settings",
        headers=headers,
        json={"enabled": True}
    )
    assert enabled.json()["enabled"] is True
    trace = make_trace()
    assert execution_history_service.save_trace(user_id, trace) is True

    history = client.get("/api/history", headers=headers).json()["history"]
    assert len(history) == 1
    assert history[0]["trace_id"] == trace.trace_id
    assert history[0]["trace"]["token_count"] == 32
    assert client.get(f"/api/history/{trace.trace_id}", headers=headers).status_code == 200

    feedback = client.put(
        f"/api/history/{trace.trace_id}/feedback",
        headers=headers,
        json={"rating": "negative"}
    )
    assert feedback.json()["feedback"] == "negative"
    assert client.delete(f"/api/history/{trace.trace_id}", headers=headers).json()["deleted"] is True
    assert client.get("/api/history", headers=headers).json()["history"] == []


def test_chat_saves_history_only_when_history_opt_in_is_enabled():
    user_id = str(uuid4())
    headers = {"X-User-ID": user_id}
    trace = make_trace()
    fake_response = AgentResponse(response="Research answer", execution_trace=trace)

    with patch.object(
        friday_orchestrator,
        "process_request",
        AsyncMock(return_value=fake_response)
    ):
        disabled = client.post("/api/chat", headers=headers, json={"prompt": "First request"})
        assert disabled.status_code == 200
        assert execution_history_service.list_history(user_id) == []

        client.put(
            "/api/history/settings",
            headers=headers,
            json={"enabled": True}
        )
        enabled = client.post("/api/chat", headers=headers, json={"prompt": "Second request"})

    assert enabled.status_code == 200
    assert [record["trace_id"] for record in execution_history_service.list_history(user_id)] == [
        trace.trace_id
    ]
