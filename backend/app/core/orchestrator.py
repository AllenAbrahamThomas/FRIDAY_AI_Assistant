import time
import uuid
import datetime
import logging
from typing import Any, Dict, List, Optional
from app.schemas.execution import ExecutionTrace, ExecutionPlan
from app.schemas.agent import AgentResponse
from app.core.intent_classifier import intent_classifier
from app.core.planner import task_planner
from app.core.execution_engine import execution_engine
from app.core.context_manager import context_manager
from app.models.model_manager import model_manager
from app.services.voice_service import voice_service
from app.agents.research_agent import research_agent
from app.agents.intelligence_agent import intelligence_agent

logger = logging.getLogger(__name__)

class FRIDAYOrchestrator:
    """
    Core decision-making engine of FRIDAY 2.0.
    Orchestrates the entire request lifecycle: intent classification,
    ordered task planning, tool execution, model selection & synthesis, and execution tracing.
    """

    def __init__(self):
        self.agents = {
            "research": research_agent,
            "world_intelligence": intelligence_agent
        }

    async def process_request(
        self,
        prompt: str,
        history: Optional[List[Any]] = None,
        memory_context: str = ""
    ) -> AgentResponse:
        start_time = time.perf_counter()
        trace_id = f"trc-{uuid.uuid4().hex}"
        created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        warnings: List[str] = []
        sources_used: List[str] = []
        response_sources: List[Dict[str, Any]] = []
        trigger_dashboard = False
        error_msg = None
        agent_used = None
        model_latency_seconds = None
        token_count = None

        logger.info(f"[{trace_id}] Received user request: '{prompt[:80]}...'")

        intent = intent_classifier.classify(prompt)
        logger.info(f"[{trace_id}] Detected intent: {intent.intent} (confidence: {intent.confidence})")

        plan = task_planner.create_plan(prompt, intent)
        logger.info(f"[{trace_id}] Formulated plan with {len(plan.steps)} steps.")
        conversation_prompt = context_manager.build_conversation_prompt(prompt, history)
        conversation_history = context_manager.format_history(history)
        if memory_context:
            saved_memory_context = f"User-saved memories:\n{memory_context[:4000]}"
            conversation_prompt = f"{saved_memory_context}\n\n{conversation_prompt}"
            conversation_history = (
                f"{saved_memory_context}\n\n{conversation_history}"
                if conversation_history
                else saved_memory_context
            )

        observations, step_warnings = await execution_engine.execute_plan(plan)
        warnings.extend(step_warnings)
        model_used = model_manager.select_model_for_task(intent.intent)
        final_response_text = ""

        agent = self.agents.get(intent.intent)
        if agent:
            agent_used = agent.name
            trigger_dashboard = intent.intent == "world_intelligence"
            research_result = None
            if intent.intent == "world_intelligence":
                research_observations = [
                    {
                        **observation,
                        "step_number": index
                    }
                    for index, observation in enumerate(
                        (
                            item for item in observations
                            if item.get("tool_name") == "web_search"
                        ),
                        start=1
                    )
                ]
                if research_observations:
                    research_result = await research_agent.run(
                        prompt,
                        context={
                            "observations": research_observations,
                            "optimized_query": prompt,
                            "skip_synthesis": True
                        }
                    )

            optimized_query = (
                plan.steps[0].tool_input.get("query", prompt)
                if intent.intent == "research" and plan.steps
                else prompt
            )
            agent_result = await agent.run(
                prompt,
                context={
                    "intent": intent.model_dump(),
                    "observations": observations,
                    "conversation_history": conversation_history,
                    "optimized_query": optimized_query,
                    "research_result": research_result
                }
            )
            final_response_text = agent_result.response_text
            model_used = agent_result.metadata.get("model_used") or model_used
            model_latency_seconds = agent_result.metadata.get("model_latency_seconds")
            token_count = agent_result.metadata.get("token_count")
            warnings.extend(agent_result.warnings)
            sources_used.extend(agent_result.metadata.get("sources_used", []))
            response_sources = agent_result.metadata.get("sources", [])
            self._update_agent_steps(
                plan,
                agent_result.success,
                agent_result.metadata,
                agent_result.warnings,
                agent_result.duration_seconds
            )

            if not agent_result.success:
                error_msg = agent_result.warnings[0] if agent_result.warnings else "Research agent failed"

        elif intent.intent == "weather":
            observation = next(
                (item for item in observations if item.get("tool_name") == "weather_and_location"),
                {}
            )
            weather_data = observation.get("data") or {}
            city = weather_data.get("city", "your area")
            temp = weather_data.get("temp")
            desc = weather_data.get("desc", "unavailable")

            if not weather_data.get("success") or temp is None:
                status_message = weather_data.get(
                    "status_message",
                    "Live weather data is unavailable."
                )
                asks_location = any(term in prompt.lower() for term in ("where am i", "what city", "my location"))
                if asks_location and weather_data.get("location_available"):
                    final_response_text = (
                        f"Your approximate location is {city}, Sir. "
                        "I couldn't retrieve current weather data."
                    )
                else:
                    final_response_text = f"I couldn't retrieve live weather data for {city}, Sir."
                warnings.append(status_message)
                error_msg = status_message
            else:
                sources_used.append(f"Open-Meteo & Geolocation ({city})")
                local_info_context = f"User Location: {city}\nCurrent Weather: {temp}°C, {desc}"
                weather_sys = context_manager.build_system_prompt()
                gen_res = await model_manager.generate(
                    prompt=f"Local Context:\n{local_info_context}\n\n{conversation_prompt}",
                    system_prompt=weather_sys,
                    task_intent=intent.intent
                )
                final_response_text = gen_res.text
                model_used = gen_res.model or model_used
                model_latency_seconds = gen_res.latency_seconds
                token_count = gen_res.token_count

                if not final_response_text:
                    final_response_text = (
                        f"Telemetry sensor check: Location detected as {city}. "
                        f"Current temperature is {temp}°C with {desc}."
                    )
                    error_msg = gen_res.error or f"Ollama connection offline or model '{model_used}' unavailable"
                    warnings.append(error_msg)

        elif intent.intent == "greeting":
            greet_sys = context_manager.build_system_prompt(is_initial=True, is_greeting=True)
            gen_res = await model_manager.generate(
                prompt=conversation_prompt,
                system_prompt=greet_sys,
                task_intent=intent.intent
            )
            final_response_text = gen_res.text
            model_used = gen_res.model or model_used
            model_latency_seconds = gen_res.latency_seconds
            token_count = gen_res.token_count
            if not final_response_text:
                final_response_text = f"Hello Allen. {context_manager.get_time_greeting()} How can I assist you today, Sir?"
            if not gen_res.success:
                error_msg = gen_res.error or "Model generation failed."
                warnings.append(error_msg)

        else:
            gen_sys = context_manager.build_system_prompt()
            gen_res = await model_manager.generate(
                prompt=conversation_prompt,
                system_prompt=gen_sys,
                task_intent=intent.intent
            )
            final_response_text = gen_res.text
            model_used = gen_res.model or model_used
            model_latency_seconds = gen_res.latency_seconds
            token_count = gen_res.token_count
            if not final_response_text:
                final_response_text = (
                    f"Diagnostic mode active, Allen. Core LLM engine is currently delayed. "
                    "Subsystems are functional."
                )
                error_msg = gen_res.error or f"Ollama connection offline or model '{model_used}' unavailable"
                warnings.append(error_msg)

        if not agent:
            self._mark_direct_steps(plan, final_response_text, error_msg)

        # Trigger voice synthesis in background thread
        voice_service.speak(final_response_text)

        total_duration = round(time.perf_counter() - start_time, 3)

        # 5. Build Execution Trace
        trace = ExecutionTrace(
            trace_id=trace_id,
            user_prompt=prompt,
            intent=intent,
            agent_used=agent_used,
            plan=plan,
            steps_executed=plan.steps,
            total_duration_seconds=total_duration,
            model_latency_seconds=model_latency_seconds,
            token_count=token_count,
            model_used=model_used,
            sources_used=sources_used,
            warnings=warnings,
            created_at=created_at
        )

        logger.info(f"[{trace_id}] Request completed in {total_duration}s using model '{model_used}'.")

        return AgentResponse(
            response=final_response_text,
            trigger_dashboard=trigger_dashboard,
            execution_trace=trace,
            sources=response_sources,
            error=error_msg
        )

    @staticmethod
    def _update_agent_steps(
        plan: ExecutionPlan,
        agent_success: bool,
        metadata: Dict[str, Any],
        agent_warnings: List[str],
        agent_duration_seconds: float
    ) -> None:
        for step in plan.steps:
            if step.tool_name:
                continue
            if step.tool_input.get("operation") == "evidence_pipeline":
                processed = metadata.get("evidence_processed", agent_success)
                step.status = "completed" if processed else "failed"
                if not processed and agent_warnings:
                    step.error = agent_warnings[0]
            elif metadata.get("synthesis_completed"):
                step.status = "completed"
                step.duration_seconds = agent_duration_seconds
            elif metadata.get("synthesis_skipped"):
                step.status = "skipped"
                step.observation = "Synthesis skipped because usable source data was unavailable."
            else:
                step.status = "failed"
                step.error = agent_warnings[0] if agent_warnings else "Agent synthesis failed."

    @staticmethod
    def _mark_direct_steps(plan: ExecutionPlan, response: str, error: str = None) -> None:
        for step in plan.steps:
            if step.tool_name:
                continue
            step.status = "completed" if response else "failed"
            if error:
                step.observation = f"Completed with warning: {error}"
            if step.status == "failed":
                step.error = error or "No response was generated."

friday_orchestrator = FRIDAYOrchestrator()
