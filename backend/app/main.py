from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import chat, monitor
from app.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for FRIDAY AI Assistant",
    version="1.0.0"
)

# Set up CORS middleware to allow connection from the Vite Dev Server (localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production if necessary
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
        "assistant": "FRIDAY AI",
        "message": "Subsystems active. Core LLM interface online."
    }
