from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class IntentResult(BaseModel):
    intent: str = Field(..., description="Detected intent: general, world_intelligence, research, coding, weather, greeting")
    requires_tools: bool = Field(default=False)
    complexity: str = Field(default="direct", description="direct, single_step, multi_step")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    entities: Dict[str, Any] = Field(default_factory=dict)

class PlanStep(BaseModel):
    step_number: int
    description: str
    tool_name: Optional[str] = None
    tool_input: Dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="pending", description="pending, running, completed, failed, skipped")
    observation: Optional[str] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0

class ExecutionPlan(BaseModel):
    task_goal: str
    steps: List[PlanStep] = Field(default_factory=list)

class ExecutionTrace(BaseModel):
    trace_id: str
    user_prompt: str
    intent: IntentResult
    agent_used: Optional[str] = None
    plan: Optional[ExecutionPlan] = None
    steps_executed: List[PlanStep] = Field(default_factory=list)
    total_duration_seconds: float = 0.0
    model_latency_seconds: Optional[float] = None
    token_count: Optional[int] = None
    model_used: str = "llama3.2"
    sources_used: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    created_at: str
