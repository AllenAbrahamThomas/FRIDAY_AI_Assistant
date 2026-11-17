from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import chat, monitor, models, memory
from app.config import settings
from app.models.model_manager import model_manager

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for FRIDAY AI Assistant",
    version=settings.VERSION
)

# Secure CORS middleware allowing configured frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(chat.router)
app.include_router(monitor.router)
app.include_router(models.router)
app.include_router(memory.router)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "assistant": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "active_model": model_manager.active_model,
        "message": "Subsystems active. Core LLM interface online."
    }

@app.get("/api/health")
async def health_check():
    ollama_health = await model_manager.default_provider.check_health()
    active_model = model_manager.active_model
    installed_models = ollama_health.available_models
    model_available = any(
        name == active_model or (
            ":" not in active_model and name == f"{active_model}:latest"
        )
        for name in installed_models
    )
    error = ollama_health.error
    if ollama_health.connected and not model_available:
        error = f"Active model '{active_model}' is not installed"

    return {
        "status": (
            "healthy"
            if ollama_health.connected and model_available
            else "degraded"
        ),
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "active_model": active_model,
        "ollama": {
            "connected": ollama_health.connected,
            "base_url": ollama_health.base_url,
            "configured_model": active_model,
            "installed_models": installed_models,
            "model_available": model_available,
            "error": error
        }
    }
