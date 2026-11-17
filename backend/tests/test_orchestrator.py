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
    assert len(plan.steps) == 5
    assert plan.steps[0].tool_name == "world_monitor_telemetry"
    assert plan.steps[1].tool_name == "world_news_feed"
    assert plan.steps[2].tool_name == "web_search"
    assert plan.steps[3].tool_name == "web_search"
    assert plan.steps[4].tool_name is None  # Synthesis step

    research_intent = intent_classifier.classify("Research quantum computing breakthroughs")
    res_plan = task_planner.create_plan("Research quantum computing breakthroughs", research_intent)
    assert len(res_plan.steps) == 4
    assert res_plan.steps[0].tool_name == "web_search"
    assert res_plan.steps[1].tool_name == "web_search"
    assert res_plan.steps[2].tool_input["operation"] == "evidence_pipeline"
    assert res_plan.steps[3].tool_input["prompt"] == "Research quantum computing breakthroughs"

def test_tool_registry():
    tools = tool_registry.list_tools()
    tool_names = [t["name"] for t in tools]
    assert "world_monitor_telemetry" in tool_names
    assert "world_news_feed" in tool_names
    assert "web_search" in tool_names
    assert "weather_and_location" in tool_names
    search_tool = next(tool for tool in tools if tool["name"] == "web_search")
    assert search_tool["timeout_seconds"] > 0
    assert "query" in search_tool["input_schema"]["properties"]
    assert search_tool["output_schema"]["type"] == "string"

@pytest.mark.asyncio
async def test_tool_registry_missing_tool():
    res = await tool_registry.execute("non_existent_tool_xyz")
    assert res["success"] is False
    assert "not found" in res["error"]

@pytest.mark.asyncio
async def test_tool_registry_rejects_invalid_tool_input_before_execution():
    result = await tool_registry.execute("web_search", query="", max_results=20)
    assert result["success"] is False
    assert "Invalid input" in result["error"]

@pytest.mark.asyncio
async def test_orchestrator_process_world_intelligence():
    fake_telemetry = {
        "global_risk_index": 70.0,
        "active_conflicts": 10,
        "economic_stability_score": 54.5,
        "is_live": True,
        "is_stale": False,
        "data_source": "live_worldmonitor_api",
        "data_as_of": "2026-11-17T10:00:00+00:00",
        "recent_events": [{
            "region": "Ukraine",
            "severity": "High",
            "risk_score": 70.0,
            "trend": "Stable",
            "description": "Stability index evaluated at 70.0.",
            "data_as_of": "2026-11-17T10:00:00+00:00",
            "is_live": True
        }]
    }
    fake_news = [{
        "title": "Historic peace talks initiated",
        "source": "Reuters",
        "link": "https://example.com/peace-talks",
        "publishedAt": 1794912000000,
        "snippet": "Officials began a new round of talks.",
        "is_live": True,
        "data_source": "live_worldmonitor_api"
    }]
    primary_search = (
        "Publish Date: Nov 17, 2026\n"
        "Source: Reuters\n"
        "News Headline: Officials begin new peace talks\n"
        "URL: https://example.com/reuters\n"
        "Snippet: Officials began negotiations.\n"
    )
    verification_search = (
        "Publish Date: Nov 17, 2026\n"
        "Source: Associated Press\n"
        "News Headline: Officials begin new peace talks\n"
        "URL: https://example.org/ap\n"
        "Snippet: A second outlet reported the negotiations.\n"
    )
    fake_llm_response = "Give me a sec, Boss. Here is the latest world intelligence briefing."

    fake_gen_result = ModelGenerationResult(
        text=fake_llm_response,
        model="llama3.2",
        latency_seconds=0.1,
        success=True
    )

    with patch("app.tools.registry.tool_registry.execute", AsyncMock(side_effect=[
        {"success": True, "data": {"telemetry": fake_telemetry, "summary_context": "Risk: 70%"}, "error": None, "duration_seconds": 0.05},
        {"success": True, "data": {"articles": fake_news, "news_context": "News feed loaded."}, "error": None, "duration_seconds": 0.05},
        {"success": True, "data": primary_search, "error": None, "duration_seconds": 0.05},
        {"success": True, "data": verification_search, "error": None, "duration_seconds": 0.05}
    ])), patch("app.models.model_manager.model_manager.generate", AsyncMock(return_value=fake_gen_result)), \
         patch("app.services.voice_service.voice_service.speak"):

        result = await friday_orchestrator.process_request("What is happening in the world today?")
        
        assert result.trigger_dashboard is True
        assert "INTELLIGENCE BRIEFING" in result.response
        assert fake_llm_response in result.response
        assert "https://example.com/peace-talks" in result.response
        assert "https://example.org/ap" in result.response
        assert result.execution_trace is not None
        assert result.execution_trace.intent.intent == "world_intelligence"
        assert result.execution_trace.agent_used == "intelligence_agent"
        assert len(result.execution_trace.steps_executed) == 5
        assert all(step.status == "completed" for step in result.execution_trace.steps_executed)
        assert result.execution_trace.total_duration_seconds >= 0
        assert result.execution_trace.model_latency_seconds == 0.1
        assert "World Monitor" in result.execution_trace.sources_used
        assert "Reuters" in result.execution_trace.sources_used
        assert any(source["source"] == "Reuters" for source in result.sources)

@pytest.mark.asyncio
async def test_orchestrator_answers_simple_request_without_tools_or_agent():
    fake_gen_result = ModelGenerationResult(
        text="Gravity attracts objects with mass.",
        model="llama3.2",
        latency_seconds=0.1,
        success=True
    )
    with patch(
        "app.models.model_manager.model_manager.generate",
        AsyncMock(return_value=fake_gen_result)
    ), patch(
        "app.tools.registry.tool_registry.execute",
        AsyncMock()
    ) as mock_execute, patch("app.services.voice_service.voice_service.speak"):
        result = await friday_orchestrator.process_request("Explain gravity in simple terms.")

    mock_execute.assert_not_awaited()
    assert result.execution_trace.intent.intent == "general"
    assert result.execution_trace.agent_used is None
    assert result.execution_trace.steps_executed[0].status == "completed"
    assert result.execution_trace.model_latency_seconds == 0.1
    assert result.response == fake_gen_result.text

@pytest.mark.asyncio
async def test_orchestrator_passes_recent_history_to_direct_model_requests():
    fake_gen_result = ModelGenerationResult(
        text="It causes objects to attract one another.",
        model="llama3.2",
        latency_seconds=0.1,
        success=True
    )
    with patch(
        "app.models.model_manager.model_manager.generate",
        AsyncMock(return_value=fake_gen_result)
    ) as mock_generate, patch("app.services.voice_service.voice_service.speak"):
        await friday_orchestrator.process_request(
            "How does that work?",
            history=[{"role": "user", "content": "Explain gravity in simple terms."}]
        )

    model_prompt = mock_generate.await_args.kwargs["prompt"]
    assert "Explain gravity in simple terms." in model_prompt
    assert "Current request:\nHow does that work?" in model_prompt

@pytest.mark.asyncio
async def test_orchestrator_routes_research_through_execution_engine_and_agent():
    primary_search = (
        "Publish Date: Nov 17, 2026\n"
        "Source: Reuters\n"
        "News Headline: Researchers report a new quantum computing milestone\n"
        "Snippet: A research team demonstrated a new error correction method.\n"
    )
    verification_search = (
        "Publish Date: Nov 17, 2026\n"
        "Source: Associated Press\n"
        "News Headline: New quantum computing milestone reported by researchers\n"
        "Snippet: The team reported progress on quantum error correction.\n"
    )
    fake_gen_result = ModelGenerationResult(
        text="Researchers reported a quantum error-correction milestone.",
        model="qwen3:8b",
        latency_seconds=0.1,
        success=True
    )

    with patch("app.tools.registry.tool_registry.execute", AsyncMock(side_effect=[
        {"success": True, "data": primary_search, "error": None, "duration_seconds": 0.02},
        {"success": True, "data": verification_search, "error": None, "duration_seconds": 0.03}
    ])) as mock_execute, patch(
        "app.models.model_manager.model_manager.generate",
        AsyncMock(return_value=fake_gen_result)
    ), patch("app.services.voice_service.voice_service.speak"):
        result = await friday_orchestrator.process_request("Research quantum computing breakthroughs")

    assert mock_execute.await_count == 2
    assert result.execution_trace.agent_used == "research_agent"
    assert [step.status for step in result.execution_trace.steps_executed] == [
        "completed", "completed", "completed", "completed"
    ]
    assert "Sources:" in result.response

@pytest.mark.asyncio
async def test_orchestrator_records_failed_tool_steps():
    failures = [
        {
            "success": False,
            "data": None,
            "error": "World Monitor unavailable",
            "duration_seconds": 0.01
        },
        {
            "success": False,
            "data": None,
            "error": "News feed unavailable",
            "duration_seconds": 0.02
        },
        {
            "success": False,
            "data": None,
            "error": "Primary search unavailable",
            "duration_seconds": 0.03
        },
        {
            "success": False,
            "data": None,
            "error": "Verification search unavailable",
            "duration_seconds": 0.04
        }
    ]
    with patch(
        "app.tools.registry.tool_registry.execute",
        AsyncMock(side_effect=failures)
    ), patch("app.services.voice_service.voice_service.speak"):
        result = await friday_orchestrator.process_request("What is happening in the world today?")

    assert [step.status for step in result.execution_trace.steps_executed] == [
        "failed", "failed", "failed", "failed", "skipped"
    ]
    assert len(result.execution_trace.warnings) >= 2
    assert result.error is not None

@pytest.mark.asyncio
async def test_orchestrator_reports_unavailable_weather_without_inventing_conditions():
    observations = [{
        "tool_name": "weather_and_location",
        "data": {
            "city": "New York",
            "temp": None,
            "desc": "unavailable",
            "success": False,
            "location_available": True,
            "status_message": "Live weather data unavailable"
        }
    }]
    with patch(
        "app.core.orchestrator.execution_engine.execute_plan",
        AsyncMock(return_value=(observations, []))
    ), patch(
        "app.core.orchestrator.model_manager.generate",
        AsyncMock(side_effect=AssertionError("Must not synthesize missing weather"))
    ), patch("app.services.voice_service.voice_service.speak"):
        result = await friday_orchestrator.process_request("What is the weather?")

    assert "couldn't retrieve live weather data" in result.response.lower()
    assert result.error == "Live weather data unavailable"
