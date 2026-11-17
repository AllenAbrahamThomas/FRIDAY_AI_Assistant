import logging
from typing import Dict, Any, List
from app.schemas.execution import IntentResult, ExecutionPlan, PlanStep
from app.services.ollama_service import ollama_service

logger = logging.getLogger(__name__)

class TaskPlanner:
    """
    Creates ordered, transparent execution plans based on user intent and query complexity.
    """

    def create_plan(self, prompt: str, intent: IntentResult) -> ExecutionPlan:
        steps: List[PlanStep] = []

        if intent.intent == "world_intelligence":
            steps.append(PlanStep(
                step_number=1,
                description="Retrieve current global risk scores and hotzone stability metrics",
                tool_name="world_monitor_telemetry",
                tool_input={}
            ))
            steps.append(PlanStep(
                step_number=2,
                description="Fetch latest intelligence news digest and breaking alerts",
                tool_name="world_news_feed",
                tool_input={}
            ))
            steps.append(PlanStep(
                step_number=3,
                description="Synthesize structured intelligence briefing with risk indicators and implications",
                tool_name=None, # Internal synthesis step
                tool_input={"prompt": prompt}
            ))
            return ExecutionPlan(
                task_goal=f"Produce geopolitical intelligence briefing for: '{prompt}'",
                steps=steps
            )

        elif intent.intent == "research":
            optimized_q = ollama_service.optimize_search_query(prompt)
            steps.append(PlanStep(
                step_number=1,
                description=f"Execute multi-source search for primary context: '{optimized_q}'",
                tool_name="web_search",
                tool_input={"query": optimized_q, "max_results": 4}
            ))
            steps.append(PlanStep(
                step_number=2,
                description=f"Corroborate facts and search for verification: '{optimized_q} verification'",
                tool_name="web_search",
                tool_input={"query": f"{optimized_q} fact check verification", "max_results": 3}
            ))
            steps.append(PlanStep(
                step_number=3,
                description="Synthesize verified report cross-checking evidence and citations",
                tool_name=None,
                tool_input={"prompt": prompt}
            ))
            return ExecutionPlan(
                task_goal=f"Conduct multi-source research and fact verification for: '{prompt}'",
                steps=steps
            )

        elif intent.intent == "weather":
            steps.append(PlanStep(
                step_number=1,
                description="Query local sensor and meteorological feeds for weather/location",
                tool_name="weather_and_location",
                tool_input={}
            ))
            steps.append(PlanStep(
                step_number=2,
                description="Format sleek conversational weather report",
                tool_name=None,
                tool_input={"prompt": prompt}
            ))
            return ExecutionPlan(
                task_goal="Retrieve local meteorological telemetry",
                steps=steps
            )

        else:
            # Direct generation
            steps.append(PlanStep(
                step_number=1,
                description=f"Direct model generation ({intent.intent})",
                tool_name=None,
                tool_input={"prompt": prompt}
            ))
            return ExecutionPlan(
                task_goal=f"Direct model response for '{intent.intent}' query",
                steps=steps
            )

task_planner = TaskPlanner()
