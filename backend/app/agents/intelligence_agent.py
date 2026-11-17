import datetime
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.agents.base_agent import AgentCitation, AgentEvidence, AgentResult, BaseAgent
from app.models.model_manager import model_manager
from app.services.worldmonitor_service import COUNTRY_NAMES


class IntelligenceAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="intelligence_agent",
            description="Builds region-aware intelligence briefings from World Monitor and cited research."
        )

    async def _execute(self, prompt: str, context: Dict[str, Any]) -> AgentResult:
        observations = context.get("observations", [])
        telemetry_observation = next(
            (item for item in observations if item.get("tool_name") == "world_monitor_telemetry"),
            None
        )
        news_observation = next(
            (item for item in observations if item.get("tool_name") == "world_news_feed"),
            None
        )
        warnings = [
            f"{item.get('tool_name', 'Tool')} failed: {item['error']}"
            for item in observations
            if item.get("error")
        ]

        telemetry_result = (telemetry_observation or {}).get("data") or {}
        telemetry = telemetry_result.get("telemetry", {}) if isinstance(telemetry_result, dict) else {}
        news_result = (news_observation or {}).get("data") or {}
        news_items = news_result.get("articles", []) if isinstance(news_result, dict) else []
        if not isinstance(news_items, list):
            news_items = []
        telemetry_error = (
            telemetry_observation.get("error")
            if telemetry_observation
            else "World Monitor telemetry was not executed."
        )
        news_error = (
            news_observation.get("error")
            if news_observation
            else "World Monitor news was not executed."
        )

        research_result = context.get("research_result")
        if not isinstance(research_result, AgentResult):
            research_result = None
        if research_result:
            warnings.extend(research_result.warnings)

        research_evidence = research_result.evidence if research_result else []
        research_citations = research_result.citations if research_result else []
        if not telemetry and not news_items and not research_evidence:
            return AgentResult(
                agent_name=self.name,
                success=False,
                response_text="I couldn't retrieve World Monitor or corroborating research data, Sir.",
                warnings=warnings or ["No usable intelligence observations were available."],
                metadata={
                    "model_used": "not_used",
                    "sources_used": [],
                    "sources": [],
                    "synthesis_skipped": True
                }
            )

        telemetry_events = telemetry.get("recent_events", [])
        if not isinstance(telemetry_events, list):
            telemetry_events = []
        region = self._extract_region(prompt, telemetry_events)
        events = self._filter_region_events(telemetry_events, region)
        filtered_news = self._filter_region_news(news_items, region)

        analysis_prompt = self._build_analysis_prompt(
            prompt=prompt,
            region=region,
            telemetry=telemetry,
            events=events,
            news_items=filtered_news,
            research_evidence=research_evidence,
            research_result=research_result,
            conversation_history=context.get("conversation_history")
        )
        generation = await model_manager.generate(
            prompt=analysis_prompt,
            system_prompt=(
                "You are FRIDAY's geopolitical analysis component. Return only a concise "
                "'Potential Implications' paragraph. Use only supplied observations and research "
                "evidence. Label every inference as analysis, not a World Monitor assessment, fact, "
                "forecast, or prediction. Do not extrapolate beyond the evidence."
            ),
            task_intent="world_intelligence"
        )

        if generation.success and generation.text.strip():
            analysis = generation.text.strip()
        else:
            warnings.append(generation.error or "Intelligence analysis model returned no response.")
            analysis = "Analysis is unavailable; no implications are inferred."

        sources = self._build_source_references(
            telemetry,
            filtered_news,
            research_citations
        )
        response_text = self._format_briefing(
            region=region,
            telemetry=telemetry,
            events=events,
            news_items=filtered_news,
            research_evidence=research_evidence,
            research_result=research_result,
            telemetry_error=telemetry_error,
            news_error=news_error,
            sources=sources,
            analysis=analysis
        )
        sources_used = sorted({
            source["source"]
            for source in sources
            if source.get("source")
        })

        if telemetry.get("is_stale"):
            warnings.append("World Monitor risk data is marked stale by the source.")
        if telemetry and telemetry.get("data_as_of") is None:
            warnings.append("World Monitor did not supply a risk-data timestamp.")
        if any(not item.get("is_live") for item in filtered_news):
            warnings.append("The news list includes static sample data and is not current reporting.")

        return AgentResult(
            agent_name=self.name,
            success=True,
            response_text=response_text,
            warnings=warnings,
            citations=research_citations,
            confidence_summary=(
                research_result.confidence_summary
                if research_result
                else "No supplemental research evidence was available."
            ),
            metadata={
                "model_used": generation.model or "fallback",
                "model_latency_seconds": generation.latency_seconds,
                "sources_used": sources_used,
                "sources": sources,
                "region": region,
                "synthesis_completed": True
            }
        )

    @staticmethod
    def _extract_region(prompt: str, events: List[Dict[str, Any]]) -> str:
        region_names = set(COUNTRY_NAMES.values())
        region_names.update(
            str(event.get("region", "")).strip()
            for event in events
            if event.get("region")
        )
        region_names.add("Middle East")
        for region in sorted(region_names, key=len, reverse=True):
            if re.search(rf"(?<!\w){re.escape(region)}(?!\w)", prompt, re.IGNORECASE):
                return region
        return "Global"

    @staticmethod
    def _filter_region_events(
        events: List[Dict[str, Any]],
        region: str
    ) -> List[Dict[str, Any]]:
        if region == "Global":
            return events
        region_key = region.casefold()
        return [
            event for event in events
            if str(event.get("region", "")).casefold() == region_key
            or str(event.get("region_code", "")).casefold() == region_key
        ]

    @staticmethod
    def _filter_region_news(
        news_items: List[Dict[str, Any]],
        region: str
    ) -> List[Dict[str, Any]]:
        if region == "Global":
            return news_items
        region_key = region.casefold()
        return [
            item for item in news_items
            if region_key in f"{item.get('title', '')} {item.get('snippet', '')}".casefold()
        ]

    def _build_analysis_prompt(
        self,
        prompt: str,
        region: str,
        telemetry: Dict[str, Any],
        events: List[Dict[str, Any]],
        news_items: List[Dict[str, Any]],
        research_evidence: List[AgentEvidence],
        research_result: Optional[AgentResult],
        conversation_history: Optional[str]
    ) -> str:
        lines = [
            f"User request: {prompt}",
            f"Requested region: {region}",
            f"World Monitor status: {self._data_status(telemetry)}",
            f"Risk data as of: {telemetry.get('data_as_of') or 'not supplied by source'}",
            f"Global risk index: {telemetry.get('global_risk_index', 'unavailable')}",
            f"Active instability regions: {telemetry.get('active_conflicts', 'unavailable')}",
            f"Economic stability score: {telemetry.get('economic_stability_score', 'unavailable')}",
            "Region indicators:"
        ]
        lines.extend(
            f"- {event.get('region', 'Unknown region')}: {event.get('severity', 'Unknown severity')}; "
            f"risk score {event.get('risk_score') if event.get('risk_score') is not None else 'unavailable'}; "
            f"{event.get('description', 'No description supplied.')}"
            for event in events
        )
        if not events:
            lines.append("- No matching region indicator was supplied.")

        lines.append("Relevant news:")
        lines.extend(
            f"- {item.get('title', 'Untitled')}; source {item.get('source', 'Unknown Source')}; "
            f"published {self._publication_time(item)}; status {self._data_status(item)}; "
            f"snippet {item.get('snippet', '')}"
            for item in news_items
        )
        if not news_items:
            lines.append("- No matching region news item was supplied.")

        lines.append("Supplemental research evidence:")
        for evidence in research_evidence:
            lines.append(
                f"- {evidence.title}; reported by {evidence.source_name}; "
                f"confidence {evidence.confidence}; snippet {evidence.snippet}"
            )
        if not research_evidence:
            lines.append("- No supplemental search evidence was available.")
        if research_result:
            lines.append(f"Research confidence: {research_result.confidence_summary}")
            lines.extend(
                f"Research limitation or conflict: {warning}"
                for warning in research_result.warnings
            )
        if conversation_history:
            lines.append(f"Recent conversation:\n{conversation_history}")
        return "\n".join(lines)

    def _format_briefing(
        self,
        region: str,
        telemetry: Dict[str, Any],
        events: List[Dict[str, Any]],
        news_items: List[Dict[str, Any]],
        research_evidence: List[AgentEvidence],
        research_result: Optional[AgentResult],
        telemetry_error: Optional[str],
        news_error: Optional[str],
        sources: List[Dict[str, Any]],
        analysis: str
    ) -> str:
        generated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        lines = [
            "## FRIDAY INTELLIGENCE BRIEFING",
            f"**Region:** {region}",
            f"**Generated (UTC):** {generated_at}",
            "",
            "### 1. Risk Overview",
            f"- Global risk index: {self._metric(telemetry, 'global_risk_index', '/100')}.",
            f"- Active instability regions: {telemetry.get('active_conflicts', 'unavailable')}.",
            f"- Economic stability score: {self._metric(telemetry, 'economic_stability_score', '/100')}.",
            f"- Data status: {self._data_status(telemetry)}.",
            f"- Data as of: {telemetry.get('data_as_of') or 'not supplied by source'}.",
            "",
            "### 2. Current Indicators"
        ]
        if events:
            for event in events:
                lines.append(
                    f"- **{event.get('region', 'Unknown region')} — {event.get('severity', 'Unknown severity')}**: "
                    f"{event.get('description', 'No description supplied.')} "
                    f"Risk score: {event.get('risk_score') if event.get('risk_score') is not None else 'unavailable'}; "
                    f"trend: {event.get('trend', 'unavailable')}; "
                    f"source timestamp: {event.get('data_as_of') or 'not supplied'}; "
                    f"status: {self._data_status(event)}."
                )
        else:
            if telemetry_error:
                lines.append(f"- World Monitor indicators are unavailable: {telemetry_error}")
            else:
                lines.append(f"- No World Monitor indicator was supplied for {region}.")

        lines.extend(["", "### 3. Recent Events"])
        if news_items:
            for item in news_items:
                url = self._safe_http_url(item.get("link"))
                title = str(item.get("title", "Untitled"))
                linked_title = f"[{title}]({url})" if url else title
                lines.append(
                    f"- {linked_title} — {item.get('source', 'Unknown Source')}; "
                    f"published {self._publication_time(item)}; status {self._data_status(item)}. "
                    f"{item.get('snippet', '')}"
                )
        else:
            if news_error:
                lines.append(f"- World Monitor news is unavailable: {news_error}")
            else:
                lines.append(f"- No matching World Monitor news was supplied for {region}.")

        lines.extend(["", "### 4. Important News"])
        if research_evidence:
            for evidence in research_evidence:
                lines.append(
                    f"- **{evidence.confidence.capitalize()} report:** {evidence.title} — "
                    f"{evidence.source_name}. {evidence.snippet}"
                )
        else:
            lines.append("- No supplemental research evidence was available.")

        lines.extend(["", "### 5. Source Comparison"])
        if research_result and research_evidence:
            lines.append(research_result.confidence_summary)
            if research_result.warnings:
                lines.extend(f"- {warning}" for warning in research_result.warnings)
        else:
            lines.append("No independent supplemental source comparison was available.")

        lines.extend([
            "",
            "### 6. Potential Implications (Analysis, Not Prediction)",
            analysis,
            "",
            "### 7. Unverified Information"
        ])
        limitations = []
        if telemetry.get("is_live") is False:
            limitations.append("World Monitor risk indicators are static sample data, not current measurements.")
        elif telemetry.get("is_stale"):
            limitations.append("World Monitor marked the risk data as stale.")
        if news_items:
            limitations.append(
                "News headlines and snippets are reported claims; full article text was not retrieved."
            )
        if research_evidence:
            limitations.append(
                "Supplemental search results are headlines/snippets and are not independently verified articles."
            )
        if not telemetry.get("data_as_of"):
            limitations.append("A source timestamp for the risk indicators was not supplied.")
        lines.extend(f"- {item}" for item in (limitations or ["No additional limitation was reported."]))

        lines.extend(["", "### 8. Sources"])
        if sources:
            for index, source in enumerate(sources, start=1):
                title = str(source.get("title", source.get("source", "Source")))
                url = self._safe_http_url(source.get("url"))
                linked_title = f"[{title}]({url})" if url else title
                lines.append(
                    f"{index}. {linked_title} — {source.get('source', 'Unknown Source')}; "
                    f"published/data as of {source.get('date') or 'not supplied'}; "
                    f"{source.get('status', 'status unavailable')}."
                )
        else:
            lines.append("No source links were supplied.")
        return "\n".join(lines)

    def _build_source_references(
        self,
        telemetry: Dict[str, Any],
        news_items: List[Dict[str, Any]],
        research_citations: List[AgentCitation]
    ) -> List[Dict[str, Any]]:
        sources: List[Dict[str, Any]] = []
        if telemetry:
            sources.append({
                "title": "World Monitor risk and event indicators",
                "source": "World Monitor",
                "url": "https://worldmonitor.app",
                "date": telemetry.get("data_as_of"),
                "status": self._data_status(telemetry)
            })
        for item in news_items:
            sources.append({
                "title": item.get("title", "World Monitor news item"),
                "source": item.get("source", "Unknown Source"),
                "url": self._safe_http_url(item.get("link")),
                "date": self._publication_time(item),
                "status": self._data_status(item)
            })
        for citation in research_citations:
            sources.append({
                "title": citation.title,
                "source": citation.source,
                "url": self._safe_http_url(citation.url),
                "date": citation.date,
                "status": "search result; not independently verified"
            })

        unique_sources = []
        seen = set()
        for source in sources:
            key = source.get("url") or (
                source.get("source"),
                source.get("title")
            )
            if key not in seen:
                seen.add(key)
                unique_sources.append(source)
        return unique_sources

    @staticmethod
    def _data_status(data: Dict[str, Any]) -> str:
        if data.get("is_live") is True:
            return "LIVE"
        if data.get("is_live") is False or data.get("data_source") == "static_fallback_sample":
            return "STATIC SAMPLE — NOT LIVE"
        return "STATUS UNAVAILABLE"

    @staticmethod
    def _metric(data: Dict[str, Any], key: str, suffix: str) -> str:
        value = data.get(key)
        return f"{value}{suffix}" if value is not None else "unavailable"

    @staticmethod
    def _publication_time(item: Dict[str, Any]) -> str:
        value = item.get("published_at") or item.get("publishedAt")
        if isinstance(value, (int, float)):
            try:
                return datetime.datetime.fromtimestamp(
                    value / 1000,
                    tz=datetime.timezone.utc
                ).isoformat()
            except (OverflowError, OSError, ValueError):
                return "Publication time unavailable"
        if isinstance(value, str) and value.strip():
            return value.strip()
        return "Publication time unavailable"

    @staticmethod
    def _safe_http_url(value: Any) -> Optional[str]:
        if not isinstance(value, str):
            return None
        try:
            parsed = urlparse(value)
        except ValueError:
            return None
        if parsed.scheme in {"http", "https"} and parsed.netloc and not re.search(r"\s", value):
            return value
        return None


intelligence_agent = IntelligenceAgent()
