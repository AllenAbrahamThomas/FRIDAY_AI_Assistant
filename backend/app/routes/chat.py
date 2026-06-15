from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.services.ollama_service import ollama_service

router = APIRouter(prefix="/api/chat", tags=["Chat"])

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    prompt: str
    history: Optional[List[ChatMessage]] = None

class ChatResponse(BaseModel):
    response: str
    trigger_dashboard: bool
    error: Optional[str] = None

@router.post("", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    if not request.prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
        
    result = await ollama_service.generate_response(request.prompt, history=request.history)
    
    return ChatResponse(
        response=result["text"],
        trigger_dashboard=result["trigger_dashboard"],
        error=result["error"]
    )
