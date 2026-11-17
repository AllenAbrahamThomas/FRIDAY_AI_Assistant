from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import chat, monitor
from app.config import settings
from app.services.ollama_service import ollama_service

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

@app.get("/")
def read_root():
    return {
        "status": "online",
        "assistant": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "message": "Subsystems active. Core LLM interface online."
    }

@app.get("/api/health")
async def health_check():
    ollama_health = await ollama_service.check_health()
    return {
        "status": "healthy" if ollama_health["connected"] else "degraded",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "ollama": ollama_health,
    }
