import time
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.config import settings
from app.models.base_provider import BaseModelProvider, ModelInfo, ModelGenerationResult, ProviderHealth
from app.models.ollama_provider import OllamaProvider

logger = logging.getLogger(__name__)

class BenchmarkResult(BaseModel):
    model: str
    prompt: str
    response_text: str
    latency_seconds: float
    token_count: Optional[int] = None
    tokens_per_second: Optional[float] = None
    success: bool
    error: Optional[str] = None

class ModelManager:
    """
    Central manager for model providers, task-specific model routing,
    dynamic model selection, and performance benchmarking.
    """

    def __init__(self):
        self.default_provider = OllamaProvider()
        self.active_model: str = settings.OLLAMA_MODEL
        self._cached_installed_models: List[str] = []

    async def get_available_models(self) -> List[ModelInfo]:
        models = await self.default_provider.list_models()
        self._cached_installed_models = [m.name for m in models]
        return models

    def set_active_model(self, model_name: str) -> bool:
        """Sets the default active model for standard queries."""
        self.active_model = model_name
        logger.info(f"Active model switched to: {model_name}")
        return True

    def select_model_for_task(self, intent: str) -> str:
        """
        Dynamically chooses the optimal model depending on query complexity:
        - Research & Coding: Prefers qwen3:8b if installed (for deep analysis & thinking)
        - Chat, Weather, Quick Briefings: Prefers llama3.2 (fast response)
        """
        # If user explicitly switched to another model as active, honor user choice
        if self.active_model != settings.OLLAMA_MODEL:
            return self.active_model

        if intent in ["research", "coding"]:
            # Check if qwen3:8b is among installed models
            for m in self._cached_installed_models:
                if "qwen3:8b" in m or "qwen" in m:
                    return m
            return self.active_model
        
        return self.active_model

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        task_intent: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.5
    ) -> ModelGenerationResult:
        """
        Routes generation through the active provider with task-specific model selection.
        """
        target_model = model
        if not target_model:
            target_model = self.select_model_for_task(task_intent or "general")

        return await self.default_provider.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            model=target_model,
            temperature=temperature
        )

    async def benchmark_model(
        self,
        model_name: str,
        prompt: str = "Explain quantum entanglement in 25 words."
    ) -> BenchmarkResult:
        """
        Runs a standardized benchmarking prompt to measure latency and token throughput.
        """
        start = time.perf_counter()
        result = await self.default_provider.generate(
            prompt=prompt,
            system_prompt="You are a precise technical benchmark responder. Be concise.",
            model=model_name,
            temperature=0.2
        )
        latency = round(time.perf_counter() - start, 3)

        tok_per_sec = None
        if result.token_count and latency > 0:
            tok_per_sec = round(result.token_count / latency, 2)

        return BenchmarkResult(
            model=model_name,
            prompt=prompt,
            response_text=result.text,
            latency_seconds=latency,
            token_count=result.token_count,
            tokens_per_second=tok_per_sec,
            success=result.success,
            error=result.error
        )

model_manager = ModelManager()
