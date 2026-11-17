from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ModelInfo(BaseModel):
    name: str = Field(..., description="Model display name")
    model_id: str = Field(..., description="Model identifier used for inference")
    parameter_size: str = Field(default="Unknown")
    size_gb: float = Field(default=0.0)
    family: str = Field(default="Unknown")
    capabilities: List[str] = Field(default_factory=list)

class ModelGenerationResult(BaseModel):
    text: str = ""
    model: str = ""
    latency_seconds: float = 0.0
    token_count: Optional[int] = None
    success: bool = True
    error: Optional[str] = None

class ProviderHealth(BaseModel):
    connected: bool
    provider_name: str
    base_url: str
    available_models: List[str] = Field(default_factory=list)
    error: Optional[str] = None

class BaseModelProvider(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.5
    ) -> ModelGenerationResult:
        """Generates completion from model."""
        pass

    @abstractmethod
    async def list_models(self) -> List[ModelInfo]:
        """Lists available models from this provider."""
        pass

    @abstractmethod
    async def check_health(self) -> ProviderHealth:
        """Verifies connection health to model provider."""
        pass
