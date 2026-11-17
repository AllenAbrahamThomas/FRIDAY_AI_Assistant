from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import logging
from app.schemas.execution import ExecutionTrace
from app.core.orchestrator import friday_orchestrator

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
    execution_trace: Optional[ExecutionTrace] = None
    error: Optional[str] = None

@router.post("", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    clean_prompt = request.prompt.strip()
    if not clean_prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty or pure whitespace")
        
    try:
        agent_res = await friday_orchestrator.process_request(clean_prompt, history=request.history)
        return ChatResponse(
            response=agent_res.response,
            trigger_dashboard=agent_res.trigger_dashboard,
            execution_trace=agent_res.execution_trace,
            error=agent_res.error
        )
    except Exception as e:
        logger.error(f"Unexpected error handling chat endpoint: {e}", exc_info=True)
        return ChatResponse(
            response="An unexpected internal error occurred while processing your request.",
            trigger_dashboard=False,
            execution_trace=None,
            error=str(e)
        )
