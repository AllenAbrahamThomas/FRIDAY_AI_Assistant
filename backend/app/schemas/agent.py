from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from app.schemas.execution import ExecutionTrace

class AgentResponse(BaseModel):
    response: str
    trigger_dashboard: bool = False
    execution_trace: Optional[ExecutionTrace] = None
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None
