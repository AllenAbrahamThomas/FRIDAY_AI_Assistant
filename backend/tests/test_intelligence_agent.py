import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.agents.base_agent import AgentCitation, AgentEvidence, AgentResult
from app.agents.intelligence_agent import IntelligenceAgent
from app.models.base_provider import ModelGenerationResult
from app.models.model_manager import model_manager


@pytest.mark.asyncio
async def test_intelligence_agent_builds_region_specific_cited_briefing():
    telemetry = {
        "global_risk_index": 68.5,
        "active_conflicts": 2,
        "economic_stability_score": 55.5,
        "is_live": True,
        "is_stale": False,
        "data_source": "live_worldmonitor_api",
        "data_as_of": "2026-11-17T10:00:00+00:00",
        "recent_events": [
            {
                "region": "Ukraine",
                "region_code": "UA",
                "severity": "High",
                "risk_score": 71.2,
                "trend": "Rising",
                "description": "Stability index is rising.",
                "data_as_of": "2026-11-17T10:00:00+00:00",
                "is_live": True
            },
            {
                "region": "Myanmar",
                "severity": "Medium",
                "risk_score": 51.0,
                "description": "A separate regional indicator."
            }
        ]
    }
    news = [
        {
            "title": "Ukraine talks continue",
            "source": "Reuters",
            "link": "https://example.com/ukraine",
            "publishedAt": 1794912000000,
            "snippet": "Officials met for discussions.",
            "is_live": True,
            "data_source": "live_worldmonitor_api"
        },
        {
            "title": "Myanmar update",
            "source": "AP",
            "link": "https://example.com/myanmar",
            "snippet": "Separate regional report.",
            "is_live": True
        }
    ]
    research = AgentResult(
        agent_name="research_agent",
        evidence=[
            AgentEvidence(
                source_name="Associated Press",
                source_url="https://example.org/research",
                title="Independent Ukraine report",
                snippet="A second publisher reported related developments.",
                confidence="likely"
            )
        ],
        citations=[
            AgentCitation(
                index=1,
                title="Independent Ukraine report",
                source="Associated Press",
                url="https://example.org/research",
                date="2026-11-17"
            )
        ],
        confidence_summary="Cross-source agreement; underlying claims remain unverified."
    )
    generation = ModelGenerationResult(
        text="Analysis: the reported developments warrant continued monitoring.",
        model="llama3.2",
        latency_seconds=0.3,
        success=True
    )

    with patch.object(model_manager, "generate", AsyncMock(return_value=generation)) as generate:
        result = await IntelligenceAgent().run(
            "Prepare an intelligence briefing on Ukraine",
            context={
                "observations": [
                    {
                        "tool_name": "world_monitor_telemetry",
                        "data": {"telemetry": telemetry}
                    },
                    {
                        "tool_name": "world_news_feed",
                        "data": {"articles": news}
                    }
                ],
                "research_result": research
            }
        )

    assert result.success is True
    assert "**Region:** Ukraine" in result.response_text
    assert "### 1. Risk Overview" in result.response_text
    assert "### 8. Sources" in result.response_text
    assert "Ukraine talks continue" in result.response_text
    assert "Independent Ukraine report" in result.response_text
    assert "Myanmar update" not in result.response_text
    assert "Static sample" not in result.response_text
    assert "Potential Implications (Analysis, Not Prediction)" in result.response_text
    assert "2026-11-17T10:00:00+00:00" in result.response_text
    assert "https://example.com/ukraine" in result.response_text
    assert "https://example.org/research" in result.response_text
    assert "World Monitor" in result.metadata["sources_used"]
    assert "Associated Press" in result.metadata["sources_used"]
    assert result.metadata["model_latency_seconds"] == 0.3
    assert "Independent Ukraine report" in generate.await_args.kwargs["prompt"]


@pytest.mark.asyncio
async def test_intelligence_agent_formats_static_fallback_when_model_is_unavailable():
    telemetry = {
        "global_risk_index": 72.4,
        "active_conflicts": 14,
        "economic_stability_score": 54.8,
        "is_live": False,
        "is_stale": True,
        "data_source": "static_fallback_sample",
        "data_as_of": None,
        "recent_events": []
    }
    generation = ModelGenerationResult(
        model="llama3.2",
        latency_seconds=0.2,
        success=False,
        error="Ollama offline"
    )

    with patch.object(model_manager, "generate", AsyncMock(return_value=generation)):
        result = await IntelligenceAgent().run(
            "What is happening globally?",
            context={
                "observations": [{
                    "tool_name": "world_monitor_telemetry",
                    "data": {"telemetry": telemetry}
                }]
            }
        )

    assert result.success is True
    assert "STATIC SAMPLE — NOT LIVE" in result.response_text
    assert "not supplied by source" in result.response_text
    assert "static sample data, not current measurements" in result.response_text
    assert "Analysis is unavailable" in result.response_text
    assert "World Monitor" in result.metadata["sources_used"]
    assert "Ollama offline" in result.warnings
