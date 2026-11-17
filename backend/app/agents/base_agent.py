"""
FRIDAY 2.0 — Base Agent
Abstract base class for all FRIDAY specialized agents.
Each agent encapsulates a domain-specific workflow:
research, world intelligence, coding, etc.
"""
from abc import ABC, abstractmethod
import time
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EvidenceSource(BaseModel):
    """A distinct source that corroborates a deduplicated evidence item."""
    source_name: str
    source_url: Optional[str] = None
    published_date: Optional[str] = None


class AgentEvidence(BaseModel):
    """A single piece of evidence gathered by an agent."""
    source_name: str = Field(..., description="Publisher or service name")
    source_url: Optional[str] = None
    title: str = ""
    snippet: str = ""
    published_date: Optional[str] = None
    confidence: str = Field(default="unverified", description="confirmed, likely, speculative, unverified")
    search_origin: str = Field(default="unknown", description="google_news_rss, duckduckgo, world_monitor, etc.")
    supporting_sources: List[EvidenceSource] = Field(default_factory=list)


class AgentCitation(BaseModel):
    """A formatted citation for display in the frontend."""
    index: int
    title: str
    source: str
    url: Optional[str] = None
    date: Optional[str] = None


class AgentResult(BaseModel):
    """Standard output from any FRIDAY agent."""
    agent_name: str
    success: bool = True
    response_text: str = ""
    evidence: List[AgentEvidence] = Field(default_factory=list)
    citations: List[AgentCitation] = Field(default_factory=list)
    confidence_summary: str = "No assessment"
    duration_seconds: float = 0.0
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseAgent(ABC):
    """
    Abstract base agent. All FRIDAY specialized agents must implement:
    - name: human-readable identifier
    - _execute: core agent logic
    """

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    async def run(self, prompt: str, context: Dict[str, Any] = None) -> AgentResult:
        """
        Public entry point with timing and exception containment.
        """
        start = time.perf_counter()
        try:
            result = await self._execute(prompt, context or {})
            result.duration_seconds = round(time.perf_counter() - start, 3)
            return result
        except Exception as e:
            duration = round(time.perf_counter() - start, 3)
            logger.error(f"Agent '{self.name}' failed: {e}", exc_info=True)
            return AgentResult(
                agent_name=self.name,
                success=False,
                response_text=f"Agent '{self.name}' encountered an error: {str(e)}",
                duration_seconds=duration,
                warnings=[str(e)]
            )

    @abstractmethod
    async def _execute(self, prompt: str, context: Dict[str, Any]) -> AgentResult:
        """Core agent logic — implemented by each specialized agent."""
        pass
