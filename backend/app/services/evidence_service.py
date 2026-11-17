"""
FRIDAY 2.0 — Evidence Service
Aggregates, deduplicates, and assesses evidence from multiple search sources.
Detects contradictions and assigns confidence levels.
"""
import re
import logging
from urllib.parse import urlparse
from typing import List, Tuple
from difflib import SequenceMatcher
from app.agents.base_agent import AgentEvidence, EvidenceSource

logger = logging.getLogger(__name__)


class EvidenceService:
    """
    Multi-source evidence processing pipeline:
    1. Parse raw search results into structured evidence
    2. Deduplicate across sources using fuzzy title matching
    3. Cross-reference facts to detect contradictions
    4. Assign confidence levels (confirmed, likely, speculative, unverified)
    """

    SIMILARITY_THRESHOLD = 0.72  # Titles above this ratio are considered duplicates

    def parse_search_results(self, raw_text: str, search_origin: str = "unknown") -> List[AgentEvidence]:
        """
        Parse the raw text output from SearchService into structured AgentEvidence items.
        Handles both Google News RSS format and DuckDuckGo format.
        """
        evidence_list: List[AgentEvidence] = []
        if not raw_text or raw_text.startswith("No real-time"):
            return evidence_list

        blocks = raw_text.split("\n---\n")
        for block in blocks:
            block = block.strip()
            if not block:
                continue

            title = ""
            source = ""
            snippet = ""
            date = ""
            source_url = None

            for line in block.split("\n"):
                line = line.strip()
                if line.startswith("News Headline:"):
                    title = line.replace("News Headline:", "").strip()
                elif line.startswith("Title:"):
                    title = line.replace("Title:", "").strip()
                elif line.startswith("Source:"):
                    source = line.replace("Source:", "").strip()
                elif line.startswith("Snippet:"):
                    snippet = line.replace("Snippet:", "").strip()
                elif line.startswith("Publish Date:"):
                    date = line.replace("Publish Date:", "").strip()
                elif line.startswith("URL:"):
                    candidate_url = line.replace("URL:", "").strip()
                    parsed_url = urlparse(candidate_url)
                    if parsed_url.scheme in {"http", "https"} and parsed_url.netloc:
                        source_url = candidate_url

            if title:
                evidence_list.append(AgentEvidence(
                    source_name=source or "Unknown Source",
                    source_url=source_url,
                    title=title,
                    snippet=snippet,
                    published_date=date or None,
                    search_origin=search_origin,
                    confidence="unverified"
                ))

        return evidence_list

    def deduplicate(self, evidence_list: List[AgentEvidence]) -> List[AgentEvidence]:
        """
        Remove near-duplicate evidence items based on fuzzy title matching.
        When duplicates are found from different sources, keeps the one with more
        context and upgrades its confidence to 'likely' (corroborated by multiple sources).
        """
        if len(evidence_list) <= 1:
            return evidence_list

        unique: List[AgentEvidence] = []
        seen_indices: set = set()

        for i, ev_a in enumerate(evidence_list):
            if i in seen_indices:
                continue

            matching_evidence = [ev_a]

            for j, ev_b in enumerate(evidence_list):
                if j <= i or j in seen_indices:
                    continue

                similarity = self._title_similarity(ev_a.title, ev_b.title)
                if similarity >= self.SIMILARITY_THRESHOLD:
                    seen_indices.add(j)
                    matching_evidence.append(ev_b)

            best = max(matching_evidence, key=lambda evidence: len(evidence.snippet))
            sources = []
            publishers = set()
            for matched in matching_evidence:
                for source in [
                    EvidenceSource(
                        source_name=matched.source_name,
                        source_url=matched.source_url,
                        published_date=matched.published_date
                    ),
                    *matched.supporting_sources
                ]:
                    source_key = (source.source_name.strip().casefold(), source.source_url or "")
                    if source_key not in publishers:
                        publishers.add(source_key)
                        sources.append(source)

            primary_key = (best.source_name.strip().casefold(), best.source_url or "")
            best.supporting_sources = [
                source
                for source in sources
                if (source.source_name.strip().casefold(), source.source_url or "") != primary_key
            ]
            distinct_publishers = {
                source.source_name.strip().casefold()
                for source in sources
                if source.source_name.strip()
                and source.source_name.strip().casefold() != "unknown source"
            }
            if len(distinct_publishers) > 1:
                best.confidence = "likely"
            unique.append(best)

        return unique

    def cross_reference(self, evidence_list: List[AgentEvidence]) -> Tuple[List[AgentEvidence], List[str]]:
        """
        Cross-reference evidence items to detect potential contradictions
        and upgrade confidence for corroborated facts.

        Returns:
            (evidence_list with updated confidence, list of contradiction warnings)
        """
        contradictions: List[str] = []

        # Simple heuristic: check for negation patterns between similar-topic items
        negation_patterns = [
            (r"\bdenied\b", r"\bconfirmed\b"),
            (r"\bno\b.*\b(deal|agreement|ceasefire)\b", r"\b(deal|agreement|ceasefire)\b.*\breached\b"),
            (r"\bdeclined\b", r"\bincreased\b"),
            (r"\bfailed\b", r"\bsucceeded\b"),
        ]

        for i, ev_a in enumerate(evidence_list):
            for j, ev_b in enumerate(evidence_list):
                if j <= i:
                    continue

                # Only compare items with similar topics (by title similarity)
                topic_sim = self._title_similarity(ev_a.title, ev_b.title)
                if topic_sim < 0.4:
                    continue

                text_a = (ev_a.title + " " + ev_a.snippet).lower()
                text_b = (ev_b.title + " " + ev_b.snippet).lower()

                for neg_a, neg_b in negation_patterns:
                    if (re.search(neg_a, text_a) and re.search(neg_b, text_b)) or \
                       (re.search(neg_b, text_a) and re.search(neg_a, text_b)):
                        ev_a.confidence = "speculative"
                        ev_b.confidence = "speculative"
                        contradictions.append(
                            f"Potential contradiction: '{ev_a.title[:60]}...' vs '{ev_b.title[:60]}...'"
                        )

        return evidence_list, contradictions

    def assess_overall_confidence(self, evidence_list: List[AgentEvidence]) -> str:
        """
        Produce a one-line confidence assessment based on evidence quality.
        """
        if not evidence_list:
            return "No evidence gathered — low confidence."

        counts = {"confirmed": 0, "likely": 0, "speculative": 0, "unverified": 0}
        for ev in evidence_list:
            counts[ev.confidence] = counts.get(ev.confidence, 0) + 1

        total = len(evidence_list)
        confirmed_ratio = counts["confirmed"] / total

        if confirmed_ratio >= 0.6:
            return f"High confidence — {counts['confirmed']}/{total} items independently confirmed."
        elif counts["speculative"] > 0:
            return f"Mixed confidence — {counts['speculative']} contradictory/speculative items detected. Verify independently."
        elif counts["likely"] > 0:
            return (
                f"Cross-source agreement — {counts['likely']}/{total} items have similar reports from "
                "multiple publishers; the underlying claims remain unverified."
            )
        else:
            return f"Unverified — {total} search-result items; no independent confirmation was available."

    def _title_similarity(self, a: str, b: str) -> float:
        """Fuzzy match ratio between two title strings."""
        if not a or not b:
            return 0.0
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()


evidence_service = EvidenceService()
