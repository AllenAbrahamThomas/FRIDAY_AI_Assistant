import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Literal

from app.core.memory_auth import get_optional_user_id
from app.schemas.execution import ExecutionTrace
from app.core.orchestrator import friday_orchestrator
from app.services.memory_service import memory_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat"])

class ChatMessage(BaseModel):
    role: Literal["user", "friday", "assistant"]
    content: str = Field(..., max_length=4000)

class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000, description="User prompt text")
    session_id: Optional[UUID] = None
    history: Optional[List[ChatMessage]] = Field(
        default=None,
        max_length=20,
        description="Prior conversation history"
    )

class ChatResponse(BaseModel):
    response: str
    trigger_dashboard: bool
    execution_trace: Optional[ExecutionTrace] = None
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    session_id: Optional[str] = None
    memory_enabled: bool = False
    error: Optional[str] = None

@router.post("", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    clean_prompt = request.prompt.strip()
    if not clean_prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty or pure whitespace")
        
    try:
        history = request.history
        memory_context = ""
        session_id = None
        memory_enabled = False
        if user_id:
            preferences = await asyncio.to_thread(memory_service.get_preferences, user_id)
            memory_enabled = preferences["memory_enabled"]
            if memory_enabled:
                if request.session_id:
                    session_id = str(request.session_id)
                    session = await asyncio.to_thread(memory_service.get_session, user_id, session_id)
                    if not session:
                        raise HTTPException(status_code=404, detail="Conversation session not found")
                else:
                    session = await asyncio.to_thread(
                        memory_service.create_session,
                        user_id,
                        clean_prompt
                    )
                    session_id = session["session_id"]

                history = await asyncio.to_thread(
                    memory_service.get_messages,
                    user_id,
                    session_id
                )
                memory_context = await asyncio.to_thread(
                    memory_service.build_memory_context,
                    user_id,
                    clean_prompt
                )

        agent_res = await friday_orchestrator.process_request(
            clean_prompt,
            history=history,
            memory_context=memory_context
        )
        if memory_enabled and user_id and session_id:
            await asyncio.to_thread(
                memory_service.append_turn,
                user_id,
                session_id,
                clean_prompt,
                agent_res.response
            )
        return ChatResponse(
            response=agent_res.response,
            trigger_dashboard=agent_res.trigger_dashboard,
            execution_trace=agent_res.execution_trace,
            sources=agent_res.sources,
            session_id=session_id,
            memory_enabled=memory_enabled,
            error=agent_res.error
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error handling chat endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected internal error occurred while processing your request."
        ) from e
