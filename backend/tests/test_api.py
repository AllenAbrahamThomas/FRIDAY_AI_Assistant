import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.services.ollama_service import ollama_service
from app.services.weather_service import weather_service

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "FRIDAY" in response.json()["assistant"]
    assert response.json()["status"] == "online"

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "ollama" in data
    assert "configured_model" in data["ollama"]

def test_monitor_telemetry():
    response = client.get("/api/monitor/telemetry")
    assert response.status_code == 200
    data = response.json()
    assert "global_risk_index" in data
    assert "recent_events" in data
    assert "is_live" in data
    assert "data_source" in data
    assert len(data["alternatives"]) > 0

def test_chat_world_intent_detection():
    assert ollama_service.detect_world_intent("What is happening in the world today?") is True
    assert ollama_service.detect_world_intent("Show me the world monitor dashboard") is True
    assert ollama_service.detect_world_intent("What is the inflation rate in the US?") is True
    assert ollama_service.detect_world_intent("How do I write a Python loop?") is False

def test_chat_empty_prompt_validation():
    # Empty string
    response = client.post("/api/chat", json={"prompt": ""})
    assert response.status_code in [400, 422]
    
    # Pure whitespace string
    response = client.post("/api/chat", json={"prompt": "   "})
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_ollama_mock_fallback():
    # Verify that the service handles offline Ollama gracefully
    result = await ollama_service.generate_response("Test query")
    assert result["text"] is not None
    assert "diagnostic" in result["text"].lower() or result["error"] is None

@pytest.mark.asyncio
async def test_weather_and_location_mocked_isolation():
    # Use mocked weather service to guarantee complete test isolation from live networks
    fake_weather = {"city": "New York", "temp": 22.0, "desc": "Clear Skies"}
    with patch.object(weather_service, "get_local_weather", AsyncMock(return_value=fake_weather)):
        result = await ollama_service.generate_response("what is the weather today?")
        assert result["text"] is not None
        assert any(term in result["text"].lower() for term in ["new york", "weather", "temperature", "diagnostic", "sensor"])

        result_loc = await ollama_service.generate_response("where am I located?")
        assert result_loc["text"] is not None
        assert any(term in result_loc["text"].lower() for term in ["new york", "location", "diagnostic", "sensor"])
