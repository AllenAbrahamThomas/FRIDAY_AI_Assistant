import os
from pathlib import Path
from typing import List

def _load_env_file():
    """
    Lightweight .env loader using standard library to avoid third-party dependencies.
    Checks repo root and backend directory.
    """
    candidates = [
        Path(__file__).resolve().parent.parent.parent / ".env",
        Path(__file__).resolve().parent.parent / ".env",
        Path.cwd() / ".env"
    ]
    for path in candidates:
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
                break
            except Exception:
                pass

_load_env_file()

class Settings:
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "FRIDAY AI Assistant")
    VERSION: str = os.getenv("VERSION", "2.0.0")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # CORS origins as a list
    _cors_raw: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
    )
    CORS_ORIGINS: List[str] = [origin.strip() for origin in _cors_raw.split(",") if origin.strip()]

    # Ollama settings
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    OLLAMA_TIMEOUT_SECONDS: float = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60.0"))
    OLLAMA_RETRY_COUNT: int = int(os.getenv("OLLAMA_RETRY_COUNT", "2"))

    # External APIs
    WORLD_MONITOR_API_KEY: str = os.getenv("WORLD_MONITOR_API_KEY", "")
    WORLD_MONITOR_TIMEOUT_SECONDS: float = float(os.getenv("WORLD_MONITOR_TIMEOUT_SECONDS", "8.0"))
    NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "")

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()
