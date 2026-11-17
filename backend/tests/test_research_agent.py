import os
import sys
import pytest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.agents.base_agent import AgentEvidence
from app.agents.research_agent import ResearchAgent
from app.models.base_provider import ModelGenerationResult
from app.models.model_manager import model_manager
from app.services.evidence_service import EvidenceService
from app.services.search_service import SearchService


def test_evidence_parser_keeps_safe_source_urls_and_metadata():
    raw_results = (
        "Publish Date: Nov 17, 2026\n"
        "Source: Reuters\n"
        "News Headline: Researchers report a quantum computing milestone\n"
        "URL: https://example.com/article\n"
        "Snippet: A team reported progress.\n"
        "\n---\n"
        "Source: Unknown Source\n"
        "Title: An unsafe link is ignored\n"
        "URL: javascript:alert(1)\n"
    )

    evidence = EvidenceService().parse_search_results(raw_results)

    assert len(evidence) == 2
    assert evidence[0].source_name == "Reuters"
    assert evidence[0].published_date == "Nov 17, 2026"
    assert evidence[0].source_url == "https://example.com/article"
    assert evidence[1].source_url is None


def test_duplicate_titles_only_gain_confidence_from_distinct_publishers():
    service = EvidenceService()
    same_publisher = [
        AgentEvidence(
            source_name="Reuters",
            title="Researchers report a quantum computing milestone",
            search_origin="primary"
        ),
        AgentEvidence(
            source_name="Reuters",
            title="Researchers report quantum computing milestone",
            search_origin="verification"
        )
    ]
    distinct_publishers = [
        AgentEvidence(
            source_name="Reuters",
            title="Researchers report a quantum computing milestone",
            search_origin="primary"
        ),
        AgentEvidence(
            source_name="Associated Press",
            title="Researchers report quantum computing milestone",
            search_origin="verification"
        )
    ]

    same_result = service.deduplicate(same_publisher)
    corroborated_result = service.deduplicate(distinct_publishers)

    assert same_result[0].confidence == "unverified"
    assert corroborated_result[0].confidence == "likely"
    assert "underlying claims remain unverified" in service.assess_overall_confidence(corroborated_result)


def test_evidence_service_reports_potential_contradictions():
    evidence = [
        AgentEvidence(
            source_name="Reuters",
            title="Officials confirmed ceasefire agreement",
            snippet="Officials confirmed a ceasefire agreement."
        ),
        AgentEvidence(
            source_name="Associated Press",
            title="Officials denied ceasefire agreement",
            snippet="Officials denied a ceasefire agreement."
        )
    ]

    updated, contradictions = EvidenceService().cross_reference(evidence)

    assert contradictions
    assert all(item.confidence == "speculative" for item in updated)


@pytest.mark.asyncio
async def test_search_service_returns_article_url_and_rss_snippet():
    rss = (
        "<rss><channel><item>"
        "<title>Research milestone reported</title>"
        "<pubDate>Tue, 17 Nov 2026 10:00:00 GMT</pubDate>"
        "<source>Reuters</source>"
        "<link>https://example.com/research</link>"
        "<description>&lt;p&gt;A team reported progress.&lt;/p&gt;</description>"
        "</item></channel></rss>"
    )
    response = type("Response", (), {"status_code": 200, "text": rss})()

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=response)):
        results = await SearchService().search("research milestone")

    assert "URL: https://example.com/research" in results
    assert "Snippet: A team reported progress." in results
    assert "Publish Date: Tue, 17 Nov 2026" in results


@pytest.mark.asyncio
async def test_research_agent_cites_sources_and_discloses_snippet_limitations():
    primary = (
        "Publish Date: Nov 17, 2026\n"
        "Source: Reuters\n"
        "News Headline: Researchers report a quantum computing milestone\n"
        "URL: https://example.com/reuters\n"
        "Snippet: A team reported progress on error correction.\n"
    )
    verification = (
        "Publish Date: Nov 17, 2026\n"
        "Source: Associated Press\n"
        "News Headline: Researchers report quantum computing milestone\n"
        "URL: https://example.org/ap\n"
        "Snippet: The team reported a similar development.\n"
    )
    generation = ModelGenerationResult(
        text="Researchers reported a quantum computing milestone.",
        model="qwen3:8b",
        latency_seconds=0.42,
        success=True
    )

    with patch.object(model_manager, "generate", AsyncMock(return_value=generation)) as generate:
        result = await ResearchAgent().run(
            "Research the quantum computing milestone.",
            context={
                "observations": [
                    {"step_number": 1, "tool_name": "web_search", "data": primary, "error": None},
                    {"step_number": 2, "tool_name": "web_search", "data": verification, "error": None}
                ]
            }
        )

    assert result.success is True
    assert "https://example.com/reuters" in result.response_text
    assert "https://example.org/ap" in result.response_text
    assert "*Reuters*" in result.response_text
    assert "*Associated Press*" in result.response_text
    assert "**Limitations:**" in result.response_text
    assert result.metadata["sources_used"] == ["Associated Press", "Reuters"]
    assert result.metadata["model_latency_seconds"] == 0.42
    assert "not verified article content" in generate.await_args.kwargs["system_prompt"]


@pytest.mark.asyncio
async def test_research_agent_surfaces_missing_evidence_without_synthesis():
    agent = ResearchAgent()
    with patch.object(model_manager, "generate", AsyncMock()) as generate:
        result = await agent.run(
            "Research an unavailable topic",
            context={
                "observations": [
                    {"step_number": 1, "error": "Search timed out"},
                    {"step_number": 2, "data": "No real-time search context could be retrieved"}
                ]
            }
        )

    assert result.success is False
    assert "Primary search failed: Search timed out" in result.warnings
    assert "Verification search returned no usable source metadata." in result.warnings
    generate.assert_not_awaited()
