import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import AsyncMock, patch
import httpx
from fastapi.testclient import TestClient
from app.main import app
from app.models.model_manager import model_manager
from app.models.base_provider import ModelInfo, ModelGenerationResult, ProviderHealth
from app.models.ollama_provider import OllamaProvider, OllamaProviderError

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

@pytest.mark.asyncio
async def test_model_benchmark_reports_generation_metrics():
    fake_result = ModelGenerationResult(
        text="A benchmark response.",
        model="qwen3:8b",
        latency_seconds=0.25,
        token_count=20,
        success=True
    )
    with patch.object(model_manager.default_provider, "generate", AsyncMock(return_value=fake_result)):
        result = await model_manager.benchmark_model("qwen3:8b")

    assert result.success is True
    assert result.model == "qwen3:8b"
    assert result.latency_seconds == 0.25
    assert result.token_count == 20
    assert result.tokens_per_second is not None
    assert result.tokens_per_second > 0

@pytest.mark.asyncio
async def test_ollama_health_reports_connection_failure():
    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("offline")):
        health = await model_manager.default_provider.check_health()
    assert health.connected is False
    assert "offline" in health.error

@pytest.mark.asyncio
async def test_ollama_health_accepts_connected_server_with_no_models():
    response = AsyncMock()
    response.status_code = 200
    response.json = lambda: {"models": []}
    with patch("httpx.AsyncClient.get", AsyncMock(return_value=response)):
        health = await model_manager.default_provider.check_health()
    assert health.connected is True
    assert health.available_models == []

@pytest.mark.asyncio
async def test_list_models_surfaces_connection_failure():
    provider = OllamaProvider()
    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("offline")):
        with pytest.raises(httpx.ConnectError):
            await provider.list_models()

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

        provider_health = ProviderHealth(
            connected=True,
            provider_name="ollama",
            base_url="http://localhost:11434",
            available_models=["llama3.2:latest", "qwen3:8b"]
        )
        with patch.object(model_manager.default_provider, "check_health", AsyncMock(return_value=provider_health)):
            missing_model = client.post("/api/models/select", json={"model": "not-installed"})
        assert missing_model.status_code == 404

        # Empty model validation
        bad_res = client.post("/api/models/select", json={"model": "  "})
        assert bad_res.status_code == 400

        # Reset active model
        model_manager.set_active_model("llama3.2")

def test_models_api_reports_ollama_unavailable():
    with patch.object(
        model_manager,
        "get_available_models",
        AsyncMock(side_effect=httpx.ConnectError("offline"))
    ):
        response = client.get("/api/models")

    assert response.status_code == 503
    assert "Unable to retrieve models" in response.json()["detail"]
