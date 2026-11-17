import os
import sys
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.core.orchestrator import friday_orchestrator
from app.schemas.agent import AgentResponse
from app.services.memory_service import DuplicateMemoryError, MemoryService, memory_service


client = TestClient(app)


@pytest.fixture
def isolated_memory_database(tmp_path, monkeypatch):
    database_path = tmp_path / "memory.sqlite3"
    monkeypatch.setattr(memory_service, "database_path", database_path)
    return database_path


def test_memory_settings_sessions_and_messages_are_user_scoped(isolated_memory_database):
    user_a = str(uuid4())
    user_b = str(uuid4())

    assert memory_service.get_preferences(user_a)["memory_enabled"] is False
    memory_service.set_memory_enabled(user_a, True)
    session = memory_service.create_session(user_a, "  Project   planning  ")
    memory_service.append_turn(user_a, session["session_id"], "Plan the release", "I will outline it.")

    assert session["title"] == "Project planning"
    assert memory_service.get_session(user_a, session["session_id"]) is not None
    assert memory_service.get_session(user_b, session["session_id"]) is None
    assert memory_service.list_sessions(user_b) == []
    assert [message["role"] for message in memory_service.get_messages(user_a, session["session_id"])] == [
        "user",
        "friday"
    ]
    assert memory_service.get_messages(user_b, session["session_id"]) == []
    assert memory_service.delete_session(user_b, session["session_id"]) is False
    assert memory_service.get_session(user_a, session["session_id"]) is not None


def test_sessions_are_isolated_persist_across_reopen_and_delete_messages(tmp_path):
    database_path = tmp_path / "memory.sqlite3"
    first_service = MemoryService(database_path)
    user_id = str(uuid4())
    first_session = first_service.create_session(user_id, "First session")
    second_session = first_service.create_session(user_id, "Second session")
    first_service.append_turn(user_id, first_session["session_id"], "First prompt", "First response")
    first_service.append_turn(user_id, second_session["session_id"], "Second prompt", "Second response")

    reopened_service = MemoryService(database_path)
    assert [message["content"] for message in reopened_service.get_messages(
        user_id,
        first_session["session_id"]
    )] == ["First prompt", "First response"]
    assert [message["content"] for message in reopened_service.get_messages(
        user_id,
        second_session["session_id"]
    )] == ["Second prompt", "Second response"]

    assert reopened_service.delete_session(user_id, first_session["session_id"]) is True
    assert reopened_service.get_messages(user_id, first_session["session_id"]) == []
    assert len(reopened_service.get_messages(user_id, second_session["session_id"])) == 2


def test_explicit_memories_are_deduplicated_and_retrieved_by_relevance(isolated_memory_database):
    user_id = str(uuid4())
    memory_service.set_memory_enabled(user_id, True)
    preference = memory_service.create_memory(user_id, "preference", "Prefers concise answers")
    project = memory_service.create_memory(user_id, "project", "Building the FRIDAY assistant")
    unrelated = memory_service.create_memory(user_id, "task", "Prepare a garden planting schedule")

    with pytest.raises(DuplicateMemoryError):
        memory_service.create_memory(user_id, "preference", "  PREFERS concise answers ")

    relevant = memory_service.retrieve_relevant_memories(user_id, "How should FRIDAY answer?")
    assert preference in relevant
    assert project in relevant
    assert unrelated not in relevant
    assert memory_service.delete_memory(user_id, project["memory_id"]) is True
    assert all(item["memory_id"] != project["memory_id"] for item in memory_service.list_memories(user_id))


def test_memory_api_requires_opt_in_and_supports_inspection_and_deletion(isolated_memory_database):
    user_id = str(uuid4())
    headers = {"X-User-ID": user_id}

    missing_identity = client.get("/api/memory/settings")
    assert missing_identity.status_code == 401

    disabled_save = client.post(
        "/api/memory/items",
        headers=headers,
        json={"category": "preference", "content": "Concise answers"}
    )
    assert disabled_save.status_code == 409

    enabled = client.put(
        "/api/memory/settings",
        headers=headers,
        json={"memory_enabled": True}
    )
    assert enabled.json()["memory_enabled"] is True

    saved = client.post(
        "/api/memory/items",
        headers=headers,
        json={"category": "preference", "content": "Concise answers"}
    )
    assert saved.status_code == 201
    memory_id = saved.json()["memory_id"]
    assert client.get("/api/memory/items", headers=headers).json()["memories"][0]["memory_id"] == memory_id
    assert client.delete(f"/api/memory/items/{memory_id}", headers=headers).json()["deleted"] is True


def test_chat_persistence_only_runs_when_enabled_and_retrieves_saved_memory(isolated_memory_database):
    user_id = str(uuid4())
    headers = {"X-User-ID": user_id, "Content-Type": "application/json"}
    fake_response = AgentResponse(response="FRIDAY response")
    with patch.object(
        friday_orchestrator,
        "process_request",
        AsyncMock(return_value=fake_response)
    ) as process_request:
        transient = client.post("/api/chat", headers=headers, json={"prompt": "Hello"})
        assert transient.status_code == 200
        assert transient.json()["memory_enabled"] is False
        assert transient.json()["session_id"] is None
        assert memory_service.list_sessions(user_id) == []

        client.put(
            "/api/memory/settings",
            headers=headers,
            json={"memory_enabled": True}
        )
        memory_service.create_memory(user_id, "preference", "Prefers concise answers")
        persisted = client.post("/api/chat", headers=headers, json={"prompt": "How should you answer?"})
        saved_memory_context = process_request.await_args.kwargs["memory_context"]

        client.put(
        "/api/memory/settings",
        headers=headers,
        json={"memory_enabled": False}
        )
        paused = client.post("/api/chat", headers=headers, json={"prompt": "Another transient request"})

    assert persisted.status_code == 200
    session_id = persisted.json()["session_id"]
    assert persisted.json()["memory_enabled"] is True
    assert len(memory_service.get_messages(user_id, session_id)) == 2
    assert "Prefers concise answers" in saved_memory_context

    assert paused.status_code == 200
    assert paused.json()["session_id"] is None
    assert process_request.await_args.kwargs["memory_context"] == ""
    assert len(memory_service.list_sessions(user_id)) == 1
