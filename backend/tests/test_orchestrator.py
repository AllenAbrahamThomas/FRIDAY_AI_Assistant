import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import AsyncMock, patch
from app.core.intent_classifier import intent_classifier
from app.core.planner import task_planner
from app.core.orchestrator import friday_orchestrator
from app.tools.registry import tool_registry
from app.tools.base_tool import BaseTool
from app.models.base_provider import ModelGenerationResult

def test_intent_classification():
    # World intelligence
    wi_res = intent_classifier.classify("What is the current threat matrix for Ukraine?")
    assert wi_res.intent == "world_intelligence"
    assert wi_res.requires_tools is True
    assert wi_res.complexity == "multi_step"

    # Weather
    w_res = intent_classifier.classify("What is the temperature and weather outside?")
    assert w_res.intent == "weather"
    assert w_res.requires_tools is True

    # Greeting
    g_res = intent_classifier.classify("Hello Friday")
    assert g_res.intent == "greeting"
    assert g_res.requires_tools is False

    # Research
    r_res = intent_classifier.classify("Research latest updates on FIFA world cup matches")
    assert r_res.intent == "research"
    assert r_res.requires_tools is True

    # Coding
    c_res = intent_classifier.classify("Write a python loop to calculate fibonacci numbers")
    assert c_res.intent == "coding"
    assert c_res.requires_tools is False

def test_task_planner():
    intent = intent_classifier.classify("Prepare an intelligence briefing on Ukraine conflict")
    plan = task_planner.create_plan("Prepare an intelligence briefing on Ukraine conflict", intent)
    assert len(plan.steps) == 3
    assert plan.steps[0].tool_name == "world_monitor_telemetry"
    assert plan.steps[1].tool_name == "world_news_feed"
    assert plan.steps[2].tool_name is None  # Synthesis step

    research_intent = intent_classifier.classify("Research quantum computing breakthroughs")
    res_plan = task_planner.create_plan("Research quantum computing breakthroughs", research_intent)
    assert len(res_plan.steps) == 3
    assert res_plan.steps[0].tool_name == "web_search"

def test_tool_registry():
    tools = tool_registry.list_tools()
    tool_names = [t["name"] for t in tools]
    assert "world_monitor_telemetry" in tool_names
    assert "world_news_feed" in tool_names
    assert "web_search" in tool_names
    assert "weather_and_location" in tool_names

@pytest.mark.asyncio
async def test_tool_registry_missing_tool():
    res = await tool_registry.execute("non_existent_tool_xyz")
    assert res["success"] is False
    assert "not found" in res["error"]

@pytest.mark.asyncio
async def test_orchestrator_process_world_intelligence():
    fake_telemetry = {"global_risk_index": 70.0, "active_conflicts": 10}
    fake_news = [{"title": "Historic peace talks initiated", "source": "Reuters"}]
    fake_llm_response = "Give me a sec, Boss. Here is the latest world intelligence briefing."

    fake_gen_result = ModelGenerationResult(
        text=fake_llm_response,
        model="llama3.2",
        latency_seconds=0.1,
        success=True
    )

    with patch("app.tools.registry.tool_registry.execute", AsyncMock(side_effect=[
        {"success": True, "data": {"telemetry": fake_telemetry, "summary_context": "Risk: 70%"}, "error": None, "duration_seconds": 0.05},
        {"success": True, "data": {"articles": fake_news, "news_context": "News feed loaded."}, "error": None, "duration_seconds": 0.05}
    ])), patch("app.models.model_manager.model_manager.generate", AsyncMock(return_value=fake_gen_result)), \
         patch("app.services.voice_service.voice_service.speak"):

        result = await friday_orchestrator.process_request("What is happening in the world today?")
        
        assert result.trigger_dashboard is True
        assert fake_llm_response in result.response
        assert result.execution_trace is not None
        assert result.execution_trace.intent.intent == "world_intelligence"
        assert len(result.execution_trace.steps_executed) == 3
        assert result.execution_trace.total_duration_seconds >= 0
        assert "World Monitor Telemetry Feed" in result.execution_trace.sources_used
