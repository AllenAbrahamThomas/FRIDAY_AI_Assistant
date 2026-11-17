import logging
import time
from typing import List, Dict, Any, Tuple
from app.schemas.execution import ExecutionPlan, PlanStep
from app.tools.registry import tool_registry

logger = logging.getLogger(__name__)

class ExecutionEngine:
    """
    Executes tasks in an ExecutionPlan by delegating tool steps to the ToolRegistry.
    Records duration, status, and raw observation output for each step.
    """

    async def execute_plan(
        self,
        plan: ExecutionPlan
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Executes all tool-bearing steps in the plan.
        Returns:
            observations: List of tool output dictionaries
            warnings: List of warning or failure strings encountered
        """
        observations: List[Dict[str, Any]] = []
        warnings: List[str] = []

        for step in plan.steps:
            if not step.tool_name:
                # Step is a reasoning / synthesis step executed by orchestrator later
                continue

            step.status = "running"
            logger.info(f"Executing step {step.step_number}: '{step.description}' via tool '{step.tool_name}'")
            step_start = time.perf_counter()

            tool_result = await tool_registry.execute(step.tool_name, **step.tool_input)
            step.duration_seconds = tool_result.get("duration_seconds", round(time.perf_counter() - step_start, 3))

            if tool_result.get("success"):
                step.status = "completed"
                data = tool_result.get("data")
                step.observation = str(data)[:200] + ("..." if len(str(data)) > 200 else "")
                observations.append({
                    "step_number": step.step_number,
                    "tool_name": step.tool_name,
                    "data": data,
                    "error": None
                })
            else:
                step.status = "failed"
                step.error = tool_result.get("error", "Unknown tool error")
                warnings.append(f"Step {step.step_number} ({step.tool_name}) failed: {step.error}")
                observations.append({
                    "step_number": step.step_number,
                    "tool_name": step.tool_name,
                    "data": None,
                    "error": step.error
                })

        return observations, warnings

execution_engine = ExecutionEngine()
