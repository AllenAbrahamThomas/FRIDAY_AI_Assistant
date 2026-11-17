import asyncio
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.memory_auth import get_required_user_id
from app.services.memory_service import DuplicateMemoryError, memory_service


router = APIRouter(prefix="/api/memory", tags=["Memory"])


class MemorySettingsRequest(BaseModel):
    memory_enabled: bool


class MemorySettingsResponse(BaseModel):
    memory_enabled: bool


class MemoryCreateRequest(BaseModel):
    category: Literal["preference", "project", "task", "research"]
    content: str = Field(..., min_length=1, max_length=2000)


@router.get("/settings", response_model=MemorySettingsResponse)
async def get_memory_settings(user_id: str = Depends(get_required_user_id)):
    return await asyncio.to_thread(memory_service.get_preferences, user_id)


@router.put("/settings", response_model=MemorySettingsResponse)
async def update_memory_settings(
    request: MemorySettingsRequest,
    user_id: str = Depends(get_required_user_id)
):
    return await asyncio.to_thread(
        memory_service.set_memory_enabled,
        user_id,
        request.memory_enabled
    )


@router.get("/sessions")
async def list_sessions(user_id: str = Depends(get_required_user_id)):
    return {"sessions": await asyncio.to_thread(memory_service.list_sessions, user_id)}


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: UUID,
    user_id: str = Depends(get_required_user_id)
):
    session_key = str(session_id)
    session = await asyncio.to_thread(memory_service.get_session, user_id, session_key)
    if not session:
        raise HTTPException(status_code=404, detail="Conversation session not found")
    messages = await asyncio.to_thread(memory_service.get_messages, user_id, session_key)
    return {"session": session, "messages": messages}


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: UUID,
    user_id: str = Depends(get_required_user_id)
):
    deleted = await asyncio.to_thread(
        memory_service.delete_session,
        user_id,
        str(session_id)
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation session not found")
    return {"deleted": True}


@router.get("/items")
async def list_memories(user_id: str = Depends(get_required_user_id)):
    return {"memories": await asyncio.to_thread(memory_service.list_memories, user_id)}


@router.post("/items", status_code=201)
async def create_memory(
    request: MemoryCreateRequest,
    user_id: str = Depends(get_required_user_id)
):
    preferences = await asyncio.to_thread(memory_service.get_preferences, user_id)
    if not preferences["memory_enabled"]:
        raise HTTPException(
            status_code=409,
            detail="Enable persistent memory before saving a memory item"
        )
    try:
        memory = await asyncio.to_thread(
            memory_service.create_memory,
            user_id,
            request.category,
            request.content
        )
    except DuplicateMemoryError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return memory


@router.delete("/items/{memory_id}")
async def delete_memory(
    memory_id: int,
    user_id: str = Depends(get_required_user_id)
):
    deleted = await asyncio.to_thread(memory_service.delete_memory, user_id, memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory item not found")
    return {"deleted": True}
