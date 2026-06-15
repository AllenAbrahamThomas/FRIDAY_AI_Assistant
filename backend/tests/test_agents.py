import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.agent_service import agent_service
from app.services.worldmonitor_service import world_monitor_service
from app.services.search_service import search_service
from app.services.ollama_service import ollama_service

def test_is_world_monitor_telemetry_query():
    assert agent_service.is_world_monitor_telemetry_query("what is the global risk index?") is True
    assert agent_service.is_world_monitor_telemetry_query("list the active hotzones") is True
    assert agent_service.is_world_monitor_telemetry_query("show the world monitor telemetry stats") is True
    assert agent_service.is_world_monitor_telemetry_query("what is the latest news on technology?") is False
    assert agent_service.is_world_monitor_telemetry_query("who won the match today?") is False

@pytest.mark.asyncio
async def test_run_agent_pipeline_telemetry_shortcut():
    fake_telemetry = "Global Risk Index: 80.0/100\nActive Conflicts: 3"
    fake_summary = "FRIDAY: The threat matrix stands at 80%."

    with patch.object(world_monitor_service, "get_world_summary_context", return_value=fake_telemetry) as mock_context, \
         patch.object(ollama_service, "raw_generate", return_value=fake_summary) as mock_generate, \
         patch.object(search_service, "search") as mock_search, \
         patch("app.services.voice_service.voice_service.speak") as mock_speak:
         
        result = await agent_service.run_agent_pipeline("what is the global risk index?")
        
        assert result["text"] == fake_summary
        assert result["trigger_dashboard"] is True
        assert result["error"] is None
        
        mock_context.assert_called_once()
        mock_generate.assert_called_once()
        # Ensure search was NEVER called (bypassed loop)
        mock_search.assert_not_called()
        mock_speak.assert_called_once_with(fake_summary)

@pytest.mark.asyncio
async def test_run_agent_pipeline_full_loop():
    fake_telemetry = "Global Risk Index: 45.0/100"
    fake_news = "NASA launches Artemis-X mission today."
    fake_draft = "NASA has successfully launched its new Artemis-X spacecraft."
    fake_facts = "Verified: Artemis-X launched successfully at 8:00 AM."
    fake_final = "FRIDAY: Artemis-X has successfully launched this morning, Allen."

    # Config sequential returns for raw_generate: draft response then final verified response
    raw_generate_mock = AsyncMock()
    raw_generate_mock.side_effect = [fake_draft, fake_final]

    with patch.object(world_monitor_service, "get_world_summary_context", return_value=fake_telemetry) as mock_telemetry, \
         patch.object(search_service, "search", side_effect=[fake_news, fake_facts]) as mock_search, \
         patch.object(ollama_service, "raw_generate", raw_generate_mock) as mock_generate, \
         patch("app.services.voice_service.voice_service.speak") as mock_speak:
         
        result = await agent_service.run_agent_pipeline("latest news on NASA spacecraft")
        
        assert result["text"] == fake_final
        assert result["trigger_dashboard"] is True
        assert result["error"] is None
        
        mock_telemetry.assert_called_once()
        # Search called twice: first for news, second for verification
        assert mock_search.call_count == 2
        # raw_generate called twice: first for draft, second for verification correction
        assert raw_generate_mock.call_count == 2
        mock_speak.assert_called_once_with(fake_final)
