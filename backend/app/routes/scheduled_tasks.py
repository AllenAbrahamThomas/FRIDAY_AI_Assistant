import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.memory_auth import get_required_user_id
from app.services.scheduled_task_service import (
    ScheduledTaskService,
    scheduled_task_service
)

router = APIRouter(prefix="/api/scheduled-tasks", tags=["Scheduled Tasks"])


class ScheduledTaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    prompt: str = Field(..., min_length=1, max_length=2000)
    interval_minutes: int = Field(
        ...,
        ge=ScheduledTaskService.MIN_INTERVAL_MINUTES,
        le=ScheduledTaskService.MAX_INTERVAL_MINUTES
    )


@router.get("")
async def list_scheduled_tasks(user_id: str = Depends(get_required_user_id)):
    tasks = await asyncio.to_thread(scheduled_task_service.list_tasks, user_id)
    return {"tasks": tasks}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_scheduled_task(
    request: ScheduledTaskCreate,
    user_id: str = Depends(get_required_user_id)
):
    title = request.title.strip()
    prompt = request.prompt.strip()
    if not title or not prompt:
        raise HTTPException(status_code=422, detail="Title and prompt cannot be blank")
    task = await asyncio.to_thread(
        scheduled_task_service.create_task,
        user_id,
        title,
        prompt,
        request.interval_minutes
    )
    return {"task": task}


@router.post("/{task_id}/pause")
async def pause_scheduled_task(
    task_id: str,
    user_id: str = Depends(get_required_user_id)
):
    task = await asyncio.to_thread(
        scheduled_task_service.set_status,
        user_id,
        task_id,
        "paused"
    )
    if not task:
        raise HTTPException(status_code=404, detail="Scheduled task not found")
    return {"task": task}


@router.post("/{task_id}/resume")
async def resume_scheduled_task(
    task_id: str,
    user_id: str = Depends(get_required_user_id)
):
    task = await asyncio.to_thread(
        scheduled_task_service.set_status,
        user_id,
        task_id,
        "active"
    )
    if not task:
        raise HTTPException(status_code=404, detail="Scheduled task not found")
    return {"task": task}


@router.delete("/{task_id}")
async def delete_scheduled_task(
    task_id: str,
    user_id: str = Depends(get_required_user_id)
):
    deleted = await asyncio.to_thread(
        scheduled_task_service.delete_task,
        user_id,
        task_id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Scheduled task not found")
    return {"deleted": True}


@router.get("/runs")
async def list_scheduled_task_runs(
    task_id: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=100),
    user_id: str = Depends(get_required_user_id)
):
    runs = await asyncio.to_thread(
        scheduled_task_service.list_runs,
        user_id,
        task_id,
        limit
    )
    return {"runs": runs}
