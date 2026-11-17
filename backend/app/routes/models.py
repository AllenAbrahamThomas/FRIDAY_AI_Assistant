from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import httpx
from app.models.model_manager import model_manager, BenchmarkResult
from app.models.base_provider import ModelInfo
from app.models.ollama_provider import OllamaProviderError

router = APIRouter(prefix="/api/models", tags=["Models"])

class ModelListResponse(BaseModel):
    active_model: str
    models: List[ModelInfo]

class SelectModelRequest(BaseModel):
    model: str

class BenchmarkRequest(BaseModel):
    model: str
    prompt: Optional[str] = "Explain quantum entanglement in 25 words."

async def _load_available_models() -> List[ModelInfo]:
    try:
        return await model_manager.get_available_models()
    except (httpx.HTTPError, OllamaProviderError) as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Unable to retrieve models from Ollama: {exc}"
        ) from exc

@router.get("", response_model=ModelListResponse)
async def list_models():
    models = await _load_available_models()
    return ModelListResponse(
        active_model=model_manager.active_model,
        models=models
    )

@router.post("/select")
async def select_model(request: SelectModelRequest):
    if not request.model or not request.model.strip():
        raise HTTPException(status_code=400, detail="Model name cannot be empty")

    model_name = request.model.strip()
    available_models = await _load_available_models()
    if not any(model.name == model_name or model.model_id == model_name for model in available_models):
        health = await model_manager.default_provider.check_health()
        if not health.connected:
            raise HTTPException(
                status_code=503,
                detail=health.error or "Ollama is unavailable; the requested model could not be validated"
            )
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' is not installed")

    model_manager.set_active_model(model_name)
    return {
        "status": "success",
        "active_model": model_manager.active_model,
        "message": f"Active model set to '{model_manager.active_model}'"
    }

@router.post("/benchmark", response_model=BenchmarkResult)
async def benchmark_model_endpoint(request: BenchmarkRequest):
    if not request.model or not request.model.strip():
        raise HTTPException(status_code=400, detail="Model name cannot be empty")
    
    result = await model_manager.benchmark_model(
        model_name=request.model.strip(),
        prompt=request.prompt or "Explain quantum entanglement in 25 words."
    )
    return result
