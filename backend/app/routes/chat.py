from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import logging
from app.services.ollama_service import ollama_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat"])

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000, description="User prompt text")
    history: Optional[List[ChatMessage]] = Field(default=None, description="Prior conversation history")

class ChatResponse(BaseModel):
    response: str
    trigger_dashboard: bool
    error: Optional[str] = None

@router.post("", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    clean_prompt = request.prompt.strip()
    if not clean_prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty or pure whitespace")
        
    try:
        result = await ollama_service.generate_response(clean_prompt, history=request.history)
        return ChatResponse(
            response=result.get("text", ""),
            trigger_dashboard=result.get("trigger_dashboard", False),
            error=result.get("error")
        )
    except Exception as e:
        logger.error(f"Unexpected error handling chat endpoint: {e}")
        return ChatResponse(
            response="An unexpected internal error occurred while processing your request.",
            trigger_dashboard=False,
            error=str(e)
        )
