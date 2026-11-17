"""
FRIDAY 2.0 — Citation Service
Converts AgentEvidence into structured, numbered citations with clickable markdown links.
"""
import logging
from typing import List
from app.agents.base_agent import AgentEvidence, AgentCitation

logger = logging.getLogger(__name__)


class CitationService:
    """
    Formats evidence into numbered citations for display in the frontend.
    Produces both structured AgentCitation objects and a markdown text block.
    """

    def build_citations(self, evidence_list: List[AgentEvidence]) -> List[AgentCitation]:
        """
        Convert a list of AgentEvidence into numbered AgentCitation objects.
        """
        citations: List[AgentCitation] = []
        for ev in evidence_list:
            sources = [
                (ev.source_name, ev.source_url, ev.published_date),
                *[
                    (source.source_name, source.source_url, source.published_date)
                    for source in ev.supporting_sources
                ]
            ]
            for source, url, date in sources:
                citations.append(AgentCitation(
                    index=len(citations) + 1,
                    title=ev.title,
                    source=source,
                    url=url,
                    date=date
                ))
        return citations

    def format_citations_markdown(self, citations: List[AgentCitation]) -> str:
        """
        Render citations as a markdown-formatted block for display.

        Example output:
        ---
        **Sources:**
        [1] "Headline" — *Source Name* (Nov 17, 2026)
        [2] "Headline" — *Source Name*
        """
        if not citations:
            return ""

        lines = ["\n---\n**Sources:**"]
        for c in citations:
            date_str = f" ({c.date})" if c.date else ""
            if c.url:
                lines.append(f"[{c.index}] [{c.title}]({c.url}) — *{c.source}*{date_str}")
            else:
                lines.append(f'[{c.index}] "{c.title}" — *{c.source}*{date_str}')

        return "\n".join(lines)

    def inject_inline_refs(self, text: str, citations: List[AgentCitation]) -> str:
        """
        If the response text mentions a headline from a citation, append a [n] inline reference.
        This is best-effort — the LLM often paraphrases, so exact match is unlikely.
        """
        for c in citations:
            # Check if a significant portion of the title appears in the response
            title_words = c.title.split()
            if len(title_words) >= 3:
                # Use first 4 significant words as a matching key
                key = " ".join(title_words[:4]).lower()
                if key.lower() in text.lower():
                    # Append [n] after the first occurrence
                    idx = text.lower().find(key.lower())
                    end = idx + len(key)
                    # Find end of sentence
                    next_period = text.find(".", end)
                    if next_period != -1 and next_period - end < 100:
                        insert_pos = next_period + 1
                        text = text[:insert_pos] + f" [{c.index}]" + text[insert_pos:]
        return text


citation_service = CitationService()
