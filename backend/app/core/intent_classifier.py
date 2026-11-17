import re
import logging
from typing import Dict, Any, Optional
from app.schemas.execution import IntentResult

logger = logging.getLogger(__name__)

class IntentClassifier:
    """
    Classifies user natural-language queries into structured intent classifications.
    Uses high-speed deterministic heuristics with extensible model-based classification.
    """

    def __init__(self):
        self._world_keywords = [
            "world monitor", "world dashboard", "situation map", "global map",
            "world news", "global news", "world events", "geopolitical",
            "international news", "latest world news", "world updates",
            "happening in the world", "happening around the world",
            "conflict", "clash", "protest", "civil unrest", "military activity",
            "threat matrix", "active conflict", "geopolitical risk", "risk score",
            "global risk index", "active hotzone", "undersea cable", "pipeline",
            "nuclear facility", "cyber threat", "intelligence briefing",
            "threat probability", "hotzones"
        ]

        self._hotzone_countries = [
            "myanmar", "ukraine", "pakistan", "mexico", "russia", "palestine", "israel", 
            "yemen", "syria", "somalia", "sudan", "venezuela", "afghanistan", "libya", 
            "iraq", "iran", "north korea", "taiwan", "china", "united states"
        ]
        self._conflict_terms = [
            "conflict", "war", "risk", "threat", "stability", "security", "safe",
            "advisory", "telemetry", "status", "situation", "hotzone", "tension", "unrest", "military", "clash"
        ]

        self._research_keywords = [
            "research", "investigate", "verify", "fact check", "fact-check", "evidence",
            "analyze", "analysis", "compare sources", "news", "sports", "match", "game",
            "scores", "tournament", "championship", "headline", "breakthrough"
        ]

        self._weather_keywords = [
            "weather", "temperature", "temp", "forecast", "climate", "outside",
            "where am i", "my city", "current position", "location"
        ]

        self._coding_keywords = [
            r"\bcode\b", r"\bpython\b", r"\bfunction\b", r"\bscript\b", r"\bbug\b",
            r"\berror\b", r"\bclass\b", r"\balgorithm\b", r"\bloop\b", r"\bdebug\b"
        ]

    def classify(self, text: str) -> IntentResult:
        p_lower = text.lower().strip()

        # 1. Greetings
        greetings = [r"\bhello\b", r"\bhi\b", r"\bhey\b", r"\bgood morning\b", r"\bgood afternoon\b", r"\bgreetings\b"]
        if any(re.search(g, p_lower) for g in greetings) and len(p_lower.split()) <= 4:
            return IntentResult(
                intent="greeting",
                requires_tools=False,
                complexity="direct",
                confidence=0.98,
                entities={"is_greeting": True}
            )

        # 2. Weather & Location
        if any(w in p_lower for w in self._weather_keywords):
            return IntentResult(
                intent="weather",
                requires_tools=True,
                complexity="single_step",
                confidence=0.95,
                entities={"query_type": "weather_or_location"}
            )

        # 3. World Intelligence
        is_wm = any(wk in p_lower for wk in self._world_keywords)
        if not is_wm and ("world" in p_lower and "happening" in p_lower):
            is_wm = True
        
        has_country = any(c in p_lower for c in self._hotzone_countries)
        has_conflict = any(ct in p_lower for ct in self._conflict_terms)
        if has_country and has_conflict:
            is_wm = True

        if is_wm:
            matched_countries = [c for c in self._hotzone_countries if c in p_lower]
            return IntentResult(
                intent="world_intelligence",
                requires_tools=True,
                complexity="multi_step",
                confidence=0.94,
                entities={"countries": matched_countries}
            )

        # 4. Research & News
        if any(rk in p_lower for rk in self._research_keywords):
            return IntentResult(
                intent="research",
                requires_tools=True,
                complexity="multi_step",
                confidence=0.90,
                entities={"research_type": "web_or_news"}
            )

        # 5. Coding
        if any(re.search(ck, p_lower) for ck in self._coding_keywords):
            return IntentResult(
                intent="coding",
                requires_tools=False,
                complexity="direct",
                confidence=0.92,
                entities={"coding_query": True}
            )

        # 6. General
        return IntentResult(
            intent="general",
            requires_tools=False,
            complexity="direct",
            confidence=0.85,
            entities={}
        )

intent_classifier = IntentClassifier()
