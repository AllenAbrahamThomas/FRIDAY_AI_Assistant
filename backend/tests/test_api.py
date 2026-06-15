import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.ollama_service import ollama_service

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["assistant"] == "FRIDAY AI"
    assert response.json()["status"] == "online"

def test_monitor_telemetry():
    response = client.get("/api/monitor/telemetry")
    assert response.status_code == 200
    data = response.json()
    assert "global_risk_index" in data
    assert "recent_events" in data
    assert len(data["alternatives"]) > 0

def test_chat_world_intent_detection():
    # Test our regex-based detection
    assert ollama_service.detect_world_intent("What is happening in the world today?") is True
    assert ollama_service.detect_world_intent("Show me the world monitor dashboard") is True
    assert ollama_service.detect_world_intent("What is the inflation rate in the US?") is True
    assert ollama_service.detect_world_intent("How do I write a Python loop?") is False

@pytest.mark.asyncio
async def test_ollama_mock_fallback():
    # Verify that the service handles offline Ollama gracefully
    result = await ollama_service.generate_response("Test query")
    assert result["text"] is not None
    assert "diagnostic" in result["text"].lower() or result["error"] is None

@pytest.mark.asyncio
async def test_weather_and_location_retrieved():
    # Verify generating response with a weather or location request completes successfully
    from app.services.weather_service import weather_service
    weather = await weather_service.get_local_weather()
    city = weather.get("city", "Manakala")
    
    result = await ollama_service.generate_response("what is the weather today?")
    assert result["text"] is not None
    assert city in result["text"] or "Manakala" in result["text"] or "sensor" in result["text"] or "temperature" in result["text"] or "weather" in result["text"].lower()

    result_loc = await ollama_service.generate_response("where am I located?")
    assert result_loc["text"] is not None
    assert city in result_loc["text"] or "Manakala" in result_loc["text"] or "Location" in result_loc["text"] or "located" in result_loc["text"].lower()

