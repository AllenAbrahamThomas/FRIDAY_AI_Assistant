import asyncio
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.memory_auth import get_required_user_id
from app.services.execution_history_service import execution_history_service


router = APIRouter(prefix="/api/history", tags=["Execution History"])


class HistorySettingsRequest(BaseModel):
    enabled: bool


class HistorySettingsResponse(BaseModel):
    enabled: bool


class FeedbackRequest(BaseModel):
    rating: Literal["positive", "negative"]


@router.get("/settings", response_model=HistorySettingsResponse)
async def get_history_settings(user_id: str = Depends(get_required_user_id)):
    return await asyncio.to_thread(execution_history_service.get_settings, user_id)


@router.put("/settings", response_model=HistorySettingsResponse)
async def update_history_settings(
    request: HistorySettingsRequest,
    user_id: str = Depends(get_required_user_id)
):
    return await asyncio.to_thread(
        execution_history_service.set_enabled,
        user_id,
        request.enabled
    )


@router.get("")
async def list_execution_history(
    limit: int = Query(default=20, ge=1, le=100),
    user_id: str = Depends(get_required_user_id)
):
    records = await asyncio.to_thread(
        execution_history_service.list_history,
        user_id,
        limit
    )
    return {"history": records}


@router.delete("")
async def clear_execution_history(user_id: str = Depends(get_required_user_id)):
    deleted_count = await asyncio.to_thread(
        execution_history_service.clear_history,
        user_id
    )
    return {"deleted_count": deleted_count}


@router.get("/{trace_id}")
async def get_execution_trace(
    trace_id: str,
    user_id: str = Depends(get_required_user_id)
):
    record = await asyncio.to_thread(
        execution_history_service.get_trace,
        user_id,
        str(trace_id)
    )
    if not record:
        raise HTTPException(status_code=404, detail="Execution history entry not found")
    return record


@router.put("/{trace_id}/feedback")
async def submit_execution_feedback(
    trace_id: str,
    request: FeedbackRequest,
    user_id: str = Depends(get_required_user_id)
):
    updated = await asyncio.to_thread(
        execution_history_service.set_feedback,
        user_id,
        str(trace_id),
        request.rating
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Execution history entry not found")
    return {"trace_id": str(trace_id), "feedback": request.rating}


@router.delete("/{trace_id}")
async def delete_execution_trace(
    trace_id: str,
    user_id: str = Depends(get_required_user_id)
):
    deleted = await asyncio.to_thread(
        execution_history_service.delete_trace,
        user_id,
        str(trace_id)
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Execution history entry not found")
    return {"deleted": True}
