import time
import httpx
import logging
import asyncio
from typing import List, Dict, Any, Optional
from app.config import settings
from app.core.url_utils import sanitize_endpoint
from app.models.base_provider import BaseModelProvider, ModelInfo, ModelGenerationResult, ProviderHealth

logger = logging.getLogger(__name__)

class OllamaProviderError(RuntimeError):
    pass

class OllamaProvider(BaseModelProvider):
    def __init__(self, base_url: Optional[str] = None, default_model: Optional[str] = None):
        super().__init__(name="ollama")
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.default_model = default_model or settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT_SECONDS
        self.retry_count = settings.OLLAMA_RETRY_COUNT

    def _get_client(self, timeout: Optional[float] = None) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=timeout or self.timeout)

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.5
    ) -> ModelGenerationResult:
        target_model = model or self.default_model
        sys_prompt = system_prompt or "You are FRIDAY, a helpful assistant."
        payload = {
            "model": target_model,
            "prompt": f"System: {sys_prompt}\nUser: {prompt}\nFriday:",
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }

        start_time = time.perf_counter()
        last_error = None

        for attempt in range(self.retry_count + 1):
            try:
                async with self._get_client() as client:
                    response = await client.post(f"{self.base_url}/api/generate", json=payload)
                    latency = round(time.perf_counter() - start_time, 3)

                    if response.status_code == 200:
                        data = response.json()
                        text = data.get("response", "").strip()
                        eval_count = data.get("eval_count")
                        return ModelGenerationResult(
                            text=text,
                            model=target_model,
                            latency_seconds=latency,
                            token_count=eval_count,
                            success=True,
                            error=None
                        )
                    elif response.status_code == 404:
                        err = f"Ollama model '{target_model}' not found (HTTP 404)"
                        logger.error(err)
                        return ModelGenerationResult(
                            text="",
                            model=target_model,
                            latency_seconds=latency,
                            success=False,
                            error=err
                        )
                    else:
                        last_error = f"Ollama returned HTTP {response.status_code}"
            except httpx.ConnectError:
                latency = round(time.perf_counter() - start_time, 3)
                err = "Cannot connect to Ollama (connection refused)"
                logger.error(err)
                return ModelGenerationResult(
                    text="",
                    model=target_model,
                    latency_seconds=latency,
                    success=False,
                    error=err
                )
            except httpx.TimeoutException:
                last_error = f"Ollama generation timed out after {self.timeout}s"
                logger.warning(f"{last_error} on attempt {attempt + 1}")
                if attempt < self.retry_count:
                    await asyncio.sleep(0.5)
            except Exception as e:
                last_error = f"Model generation failed ({type(e).__name__})"
                if attempt < self.retry_count:
                    await asyncio.sleep(0.5)

        latency = round(time.perf_counter() - start_time, 3)
        return ModelGenerationResult(
            text="",
            model=target_model,
            latency_seconds=latency,
            success=False,
            error=last_error or "Generation failed after retries"
        )

    async def list_models(self) -> List[ModelInfo]:
        async with self._get_client(timeout=5.0) as client:
            response = await client.get(f"{self.base_url}/api/tags")
        if response.status_code != 200:
            raise OllamaProviderError(f"Ollama returned HTTP {response.status_code} while listing models")

        try:
            data = response.json()
        except ValueError as exc:
            raise OllamaProviderError("Ollama returned invalid JSON while listing models") from exc

        models: List[ModelInfo] = []
        for item in data.get("models", []):
            name = item.get("name")
            if not name:
                logger.warning("Ignoring Ollama model entry without a name")
                continue
            raw_size = item.get("size", 0)
            details = item.get("details", {})
            models.append(ModelInfo(
                name=name,
                model_id=item.get("model") or name,
                parameter_size=details.get("parameter_size", "Unknown"),
                size_gb=round(raw_size / (1024 ** 3), 2),
                family=details.get("family", "Unknown"),
                capabilities=item.get("capabilities", ["completion"])
            ))
        return models

    async def check_health(self) -> ProviderHealth:
        try:
            async with self._get_client(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
            if response.status_code != 200:
                return ProviderHealth(
                    connected=False,
                    provider_name=self.name,
                    base_url=sanitize_endpoint(self.base_url),
                    error=f"Ollama returned HTTP {response.status_code}"
                )

            model_names = [
                item.get("name", "")
                for item in response.json().get("models", [])
                if item.get("name")
            ]
            return ProviderHealth(
                connected=True,
                provider_name=self.name,
                base_url=sanitize_endpoint(self.base_url),
                available_models=model_names,
                error=None
            )
        except httpx.ConnectError:
            logger.warning("Ollama health check failed (connection refused)")
            return ProviderHealth(
                connected=False,
                provider_name=self.name,
                base_url=sanitize_endpoint(self.base_url),
                available_models=[],
                error="Ollama offline (connection refused)"
            )
        except Exception as e:
            logger.warning("Ollama health check failed (%s)", type(e).__name__)
            return ProviderHealth(
                connected=False,
                provider_name=self.name,
                base_url=sanitize_endpoint(self.base_url),
                available_models=[],
                error=f"Ollama health check failed ({type(e).__name__})"
            )
