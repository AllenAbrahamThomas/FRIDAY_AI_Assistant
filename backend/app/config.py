import os

class Settings:
    PROJECT_NAME: str = "FRIDAY AI Assistant"
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "")  # Fallback to scraping/mock if not provided
    WORLD_MONITOR_API_KEY: str = os.getenv("WORLD_MONITOR_API_KEY", "")

settings = Settings()
