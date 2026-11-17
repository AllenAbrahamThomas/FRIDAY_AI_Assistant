import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.models.model_manager import model_manager
from app.models.base_provider import ModelInfo, ModelGenerationResult

client = TestClient(app)

def test_model_task_routing():
    model_manager.active_model = "llama3.2"
    model_manager._cached_installed_models = ["llama3.2:latest", "qwen3:8b"]

    # Research intent should prefer qwen3:8b
    research_model = model_manager.select_model_for_task("research")
    assert "qwen3:8b" in research_model or "qwen" in research_model

    # Chat / General should use llama3.2
    chat_model = model_manager.select_model_for_task("general")
    assert chat_model == "llama3.2"

def test_model_manager_set_active_model():
    model_manager.set_active_model("qwen3:8b")
    assert model_manager.active_model == "qwen3:8b"

    # Reset back to default
    model_manager.set_active_model("llama3.2")
    assert model_manager.active_model == "llama3.2"

@pytest.mark.asyncio
async def test_model_manager_generate():
    fake_result = ModelGenerationResult(
        text="Quantum entanglement is a physical phenomenon.",
        model="llama3.2",
        latency_seconds=0.15,
        token_count=12,
        success=True
    )

    with patch.object(model_manager.default_provider, "generate", AsyncMock(return_value=fake_result)):
        result = await model_manager.generate("Test prompt")
        assert result.success is True
        assert "entanglement" in result.text
        assert result.model == "llama3.2"
        assert result.latency_seconds == 0.15

def test_models_api_endpoints():
    fake_models = [
        ModelInfo(name="llama3.2:latest", model_id="llama3.2:latest", parameter_size="3.2B", size_gb=2.02, family="llama"),
        ModelInfo(name="qwen3:8b", model_id="qwen3:8b", parameter_size="8.2B", size_gb=5.23, family="qwen3")
    ]

    with patch.object(model_manager, "get_available_models", AsyncMock(return_value=fake_models)):
        res = client.get("/api/models")
        assert res.status_code == 200
        data = res.json()
        assert "active_model" in data
        assert len(data["models"]) == 2
        assert data["models"][0]["name"] == "llama3.2:latest"

        # Select model
        sel_res = client.post("/api/models/select", json={"model": "qwen3:8b"})
        assert sel_res.status_code == 200
        assert sel_res.json()["active_model"] == "qwen3:8b"

        # Empty model validation
        bad_res = client.post("/api/models/select", json={"model": "  "})
        assert bad_res.status_code == 400

        # Reset active model
        model_manager.set_active_model("llama3.2")
