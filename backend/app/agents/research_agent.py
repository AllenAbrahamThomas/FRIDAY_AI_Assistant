"""
FRIDAY 2.0 — Research Agent
Multi-source research agent with evidence deduplication, contradiction detection,
confidence scoring, and structured citations.

Workflow:
1. Consume primary and verification search results from the execution engine
2. Parse and structure evidence from both observations
3. Deduplicate across sources
4. Cross-reference for contradictions
5. Assess overall confidence
6. Build structured citations
7. Synthesize the final research report
"""
import logging
from typing import Dict, Any, List
from app.agents.base_agent import BaseAgent, AgentResult, AgentEvidence
from app.services.evidence_service import evidence_service
from app.services.citation_service import citation_service
from app.models.model_manager import model_manager

logger = logging.getLogger(__name__)


class ResearchAgent(BaseAgent):
    """
    Conducts multi-source web research with evidence reasoning.
    """

    def __init__(self):
        super().__init__(
            name="research_agent",
            description="Multi-source research with evidence deduplication, contradiction detection, and citation generation."
        )

    async def _execute(self, prompt: str, context: Dict[str, Any]) -> AgentResult:
        warnings: List[str] = []
        all_evidence: List[AgentEvidence] = []
        observations = {
            observation.get("step_number"): observation
            for observation in context.get("observations", [])
        }
        optimized_query = context.get("optimized_query", prompt)
        successful_searches = 0

        for step_number, origin, label in (
            (1, "google_news_rss", "Primary"),
            (2, "verification_search", "Verification")
        ):
            observation = observations.get(step_number)
            if not observation:
                warnings.append(f"{label} search was not executed.")
                continue
            if observation.get("error"):
                warnings.append(f"{label} search failed: {observation['error']}")
                continue
            if not isinstance(observation.get("data"), str):
                warnings.append(f"{label} search returned no usable text.")
                continue

            evidence = evidence_service.parse_search_results(
                observation["data"],
                search_origin=origin
            )
            if not evidence:
                warnings.append(f"{label} search returned no usable source metadata.")
                continue
            successful_searches += 1
            all_evidence.extend(evidence)
            logger.info("[%s] %s search returned %s items", self.name, label, len(evidence))

        # ── Step 4: Deduplicate evidence ──
        deduped = evidence_service.deduplicate(all_evidence)
        logger.info(f"[{self.name}] After dedup: {len(deduped)} unique items (from {len(all_evidence)} total)")

        # ── Step 5: Cross-reference for contradictions ──
        deduped, contradictions = evidence_service.cross_reference(deduped)
        if contradictions:
            warnings.extend(contradictions)
            logger.warning(f"[{self.name}] Contradictions detected: {contradictions}")

        # ── Step 6: Assess confidence ──
        confidence_summary = evidence_service.assess_overall_confidence(deduped)

        # ── Step 7: Build citations ──
        citations = citation_service.build_citations(deduped)
        citations_markdown = citation_service.format_citations_markdown(citations)

        if not deduped:
            response_text = (
                "I couldn't retrieve usable evidence for this research request, Sir. "
                "Please try again later or provide a source to investigate."
            )
            warnings.append("No usable evidence was returned by either search.")
            return AgentResult(
                agent_name=self.name,
                success=False,
                response_text=response_text,
                warnings=warnings,
                confidence_summary=confidence_summary,
                metadata={
                    "query_optimized": optimized_query,
                    "total_raw_evidence": len(all_evidence),
                    "deduped_evidence": 0,
                    "contradictions_found": 0,
                    "model_used": "not_used",
                    "successful_searches": successful_searches,
                    "evidence_processed": True,
                    "synthesis_skipped": True
                }
            )

        sources_used = sorted({
            citation.source
            for citation in citations
            if citation.source and citation.source != "Unknown Source"
        })
        if context.get("skip_synthesis"):
            return AgentResult(
                agent_name=self.name,
                success=True,
                evidence=deduped,
                citations=citations,
                confidence_summary=confidence_summary,
                warnings=warnings,
                metadata={
                    "query_optimized": optimized_query,
                    "total_raw_evidence": len(all_evidence),
                    "deduped_evidence": len(deduped),
                    "contradictions_found": len(contradictions),
                    "contradictions": contradictions,
                    "model_used": "not_used",
                    "successful_searches": successful_searches,
                    "sources_used": sources_used,
                    "evidence_processed": True,
                    "synthesis_skipped": True
                }
            )

        # ── Step 8: Build evidence context for LLM synthesis ──
        evidence_context = self._build_evidence_context(deduped, contradictions)

        # ── Step 9: LLM Synthesis ──
        system_prompt = (
            "You are FRIDAY (Female Real-time Intelligence Device & Assistant Yard), "
            "a highly sophisticated AI assistant inspired by Tony Stark's assistant in Iron Man. "
            "The user's name is Allen. Address him as Allen, Boss, or Sir.\n\n"
            "You are presenting a research report. Follow these guidelines:\n"
            "1. Lead with a brief acknowledgement (e.g., 'I've compiled the intelligence, Sir.').\n"
            "2. Present the key findings in clear, concise paragraphs — not bullet lists.\n"
            "3. Headlines and search snippets are reported claims, not verified article content. "
            "Do not present them as confirmed facts.\n"
            "4. Attribute claims to the named publisher and distinguish reported claims, corroboration, "
            "and analysis.\n"
            "5. When sources contradict, explicitly flag the disagreement as potential unless full sources "
            "confirm it.\n"
            "6. State that full article text was not retrieved when only headlines or snippets are available.\n"
            "7. End with the confidence assessment and limitations.\n"
            "8. Maintain a sleek, confident, professional tone throughout.\n"
            "9. Do NOT fabricate information — only report what the supplied search evidence shows."
        )

        synthesis_prompt = (
            f"Research Evidence Collected:\n{evidence_context}\n\n"
            f"Recent Conversation:\n{context.get('conversation_history') or 'No previous conversation context.'}\n\n"
            f"User's Original Request: {prompt}\n\n"
            f"Confidence Assessment: {confidence_summary}\n\n"
            "Synthesize a well-structured research report based ONLY on the evidence above."
        )

        gen_res = await model_manager.generate(
            prompt=synthesis_prompt,
            system_prompt=system_prompt,
            task_intent="research"
        )

        if gen_res.success and gen_res.text:
            # Inject inline citation references where possible
            response_text = citation_service.inject_inline_refs(gen_res.text, citations)
        else:
            # Fallback: present raw evidence if LLM is offline
            warnings.append(gen_res.error or "LLM synthesis unavailable")
            response_text = self._build_fallback_response(deduped, confidence_summary)

        response_text += citations_markdown
        response_text += (
            "\n\n**Limitations:** This report is based on search-result headlines and snippets; "
            "full article text was not retrieved, so claims have not been independently verified."
        )

        return AgentResult(
            agent_name=self.name,
            success=True,
            response_text=response_text,
            evidence=deduped,
            citations=citations,
            confidence_summary=confidence_summary,
            warnings=warnings,
            metadata={
                "query_optimized": optimized_query,
                "total_raw_evidence": len(all_evidence),
                "deduped_evidence": len(deduped),
                "contradictions_found": len(contradictions),
                "contradictions": contradictions,
                "model_used": gen_res.model or "fallback",
                "model_latency_seconds": gen_res.latency_seconds,
                "successful_searches": successful_searches,
                "sources_used": sources_used,
                "evidence_processed": True,
                "synthesis_completed": True
            }
        )

    def _build_evidence_context(
        self,
        evidence: List[AgentEvidence],
        contradictions: List[str]
    ) -> str:
        """Format evidence into a structured context block for LLM synthesis."""
        lines = []
        for idx, ev in enumerate(evidence, start=1):
            conf_tag = f"[{ev.confidence.upper()}]"
            date_str = f" | {ev.published_date}" if ev.published_date else ""
            lines.append(
                f"[{idx}] {conf_tag} {ev.title}\n"
                f"    Source: {ev.source_name}{date_str}\n"
                f"    URL: {ev.source_url or 'Unavailable'}\n"
                f"    Origin: {ev.search_origin}"
            )
            for supporting_source in ev.supporting_sources:
                supporting_date = (
                    f" | {supporting_source.published_date}"
                    if supporting_source.published_date
                    else ""
                )
                lines.append(
                    f"    Also reported by: {supporting_source.source_name}{supporting_date}\n"
                    f"    URL: {supporting_source.source_url or 'Unavailable'}"
                )
            if ev.snippet:
                lines.append(f"    Context: {ev.snippet}")

        context = "\n\n".join(lines)

        if contradictions:
            context += "\n\n⚠ CONTRADICTIONS DETECTED:\n"
            for c in contradictions:
                context += f"  - {c}\n"

        return context

    def _build_fallback_response(self, evidence: List[AgentEvidence], confidence: str) -> str:
        """Build a plain-text fallback when LLM is unavailable."""
        lines = [
            "I've gathered the following intelligence from open sources, Sir.\n",
            "However, the LLM synthesis engine is currently offline, so I'm presenting search-result "
            "headlines and snippets directly.\n"
        ]
        for idx, ev in enumerate(evidence, start=1):
            conf_tag = f"[{ev.confidence.upper()}]"
            date_str = f" ({ev.published_date})" if ev.published_date else ""
            lines.append(f"{idx}. {conf_tag} {ev.title} — {ev.source_name}{date_str}")

        lines.append(f"\nConfidence: {confidence}")
        return "\n".join(lines)


research_agent = ResearchAgent()
