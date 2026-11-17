import time
import uuid
import datetime
import logging
from typing import Dict, Any, List, Optional
from app.schemas.execution import ExecutionTrace, IntentResult, ExecutionPlan, PlanStep
from app.schemas.agent import AgentResponse
from app.core.intent_classifier import intent_classifier
from app.core.planner import task_planner
from app.core.execution_engine import execution_engine
from app.core.context_manager import context_manager
from app.models.model_manager import model_manager
from app.services.voice_service import voice_service

logger = logging.getLogger(__name__)

class FRIDAYOrchestrator:
    """
    Core decision-making engine of FRIDAY 2.0.
    Orchestrates the entire request lifecycle: intent classification,
    ordered task planning, tool execution, model selection & synthesis, and execution tracing.
    """

    async def process_request(self, prompt: str, history: List[Any] = None) -> AgentResponse:
        start_time = time.perf_counter()
        trace_id = f"trc-{uuid.uuid4().hex[:8]}"
        created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        warnings: List[str] = []
        sources_used: List[str] = []
        trigger_dashboard = False
        error_msg = None

        logger.info(f"[{trace_id}] Received user request: '{prompt[:80]}...'")

        # 1. Intent Classification
        intent = intent_classifier.classify(prompt)
        logger.info(f"[{trace_id}] Detected intent: {intent.intent} (confidence: {intent.confidence})")

        # 2. Task Planning
        plan = task_planner.create_plan(prompt, intent)
        logger.info(f"[{trace_id}] Formulated plan with {len(plan.steps)} steps.")

        # 3. Tool Execution
        observations, step_warnings = await execution_engine.execute_plan(plan)
        warnings.extend(step_warnings)

        # 4. Result Synthesis with Model Manager
        final_response_text = ""
        synthesis_step = next((s for s in plan.steps if s.tool_name is None), None)
        model_used = model_manager.select_model_for_task(intent.intent)

        if intent.intent == "world_intelligence":
            trigger_dashboard = True
            sources_used.append("World Monitor Telemetry Feed")
            sources_used.append("World Monitor Global News")

            wm_prompt = context_manager.build_synthesis_prompt(prompt, observations, intent.intent)
            wm_system_prompt = (
                "You are FRIDAY (Female Real-time Intelligence Device & Assistant Yard), "
                "a highly sophisticated AI assistant inspired by Tony Stark's assistant in Iron Man. "
                "The user's name is Allen. Address him as Boss, Sir, or Allen.\n"
                "Follow this exact response format:\n"
                "1. Start with an acknowledgement: 'Give me a sec, Boss. Let me check.'\n"
                "2. Provide a short, sleek, conversational paragraph summarizing the provided World Monitor telemetry index and hotzones.\n"
                "3. Present the latest world news headlines from the provided News Feed context. "
                "For each news item, you MUST include the news channel source name and the publish date/time in a natural, conversational way.\n"
                "4. End the response with: 'Let me open up the world monitor so you can better visualize what's happening, Boss.'\n"
                "Do not use markdown bullet lists; write in smooth, conversational paragraphs or clean formatted inline items. "
                "Reflect a professional, confident tone."
            )
            gen_res = await model_manager.generate(
                prompt=wm_prompt,
                system_prompt=wm_system_prompt,
                task_intent=intent.intent
            )
            final_response_text = gen_res.text
            model_used = gen_res.model or model_used

            if not final_response_text:
                context_str = observations[0]["data"].get("summary_context", "") if observations else ""
                news_str = observations[1]["data"].get("news_context", "") if len(observations) > 1 else ""
                final_response_text = (
                    "Give me a sec, Boss. Let me check.\n\n"
                    f"Here is the telemetry context, Sir:\n{context_str}\n\n"
                    f"Latest World News Feed:\n{news_str}\n\n"
                    "Let me open up the world monitor so you can better visualize what's happening, Boss."
                )
                error_msg = gen_res.error or f"Ollama connection offline or model '{model_used}' unavailable"

        elif intent.intent == "research":
            sources_used.append("Google News RSS Search")
            sources_used.append("DuckDuckGo OSINT / Web")

            research_prompt = context_manager.build_synthesis_prompt(prompt, observations, intent.intent)
            research_system = (
                "You are FRIDAY (Female Real-time Intelligence Device & Assistant Yard), "
                "a highly sophisticated AI assistant inspired by Tony Stark's assistant in Iron Man. "
                "Analyze the provided search observations and user request: "
                "1. Verify key facts across the observations. "
                "2. Distinguish confirmed facts from speculation. "
                "3. Present a clear, well-supported, evidence-grounded answer. "
                "4. Address the user as Allen or Sir in a sleek, confident, professional tone."
            )
            gen_res = await model_manager.generate(
                prompt=research_prompt,
                system_prompt=research_system,
                task_intent=intent.intent
            )
            final_response_text = gen_res.text
            model_used = gen_res.model or model_used

            if not final_response_text:
                obs_text = str(observations[0]["data"]) if observations else "No search context available."
                final_response_text = f"I retrieved these news items regarding your query, Sir: {obs_text}"
                error_msg = gen_res.error or f"Ollama connection offline or model '{model_used}' unavailable"

        elif intent.intent == "weather":
            weather_data = observations[0].get("data") if observations else {}
            city = weather_data.get("city", "Local Sensor")
            temp = weather_data.get("temp", "--")
            desc = weather_data.get("desc", "Clear")
            sources_used.append(f"Open-Meteo & Geolocation ({city})")

            local_info_context = f"User Location: {city}\nCurrent Weather: {temp}°C, {desc}"
            weather_sys = context_manager.build_system_prompt()
            gen_res = await model_manager.generate(
                prompt=f"Local Context:\n{local_info_context}\n\nUser request: {prompt}",
                system_prompt=weather_sys,
                task_intent=intent.intent
            )
            final_response_text = gen_res.text
            model_used = gen_res.model or model_used

            if not final_response_text:
                final_response_text = (
                    f"Telemetry sensor check: Location detected as {city}. "
                    f"Current temperature is {temp}°C with {desc}."
                )
                error_msg = gen_res.error or f"Ollama connection offline or model '{model_used}' unavailable"

        elif intent.intent == "greeting":
            greet_sys = context_manager.build_system_prompt(is_initial=True, is_greeting=True)
            gen_res = await model_manager.generate(
                prompt=prompt,
                system_prompt=greet_sys,
                task_intent=intent.intent
            )
            final_response_text = gen_res.text
            model_used = gen_res.model or model_used
            if not final_response_text:
                final_response_text = f"Hello Allen. {context_manager.get_time_greeting()} How can I assist you today, Sir?"

        else:
            # Coding or general task
            gen_sys = context_manager.build_system_prompt()
            gen_res = await model_manager.generate(
                prompt=prompt,
                system_prompt=gen_sys,
                task_intent=intent.intent
            )
            final_response_text = gen_res.text
            model_used = gen_res.model or model_used
            if not final_response_text:
                final_response_text = (
                    f"Diagnostic mode active, Allen. Core LLM engine is currently delayed. "
                    "Subsystems are functional."
                )
                error_msg = gen_res.error or f"Ollama connection offline or model '{model_used}' unavailable"

        if synthesis_step:
            synthesis_step.status = "completed"
            synthesis_step.duration_seconds = round(time.perf_counter() - start_time, 3)

        # Trigger voice synthesis in background thread
        voice_service.speak(final_response_text)

        total_duration = round(time.perf_counter() - start_time, 3)

        # 5. Build Execution Trace
        trace = ExecutionTrace(
            trace_id=trace_id,
            user_prompt=prompt,
            intent=intent,
            plan=plan,
            steps_executed=plan.steps,
            total_duration_seconds=total_duration,
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
            error=error_msg
        )

friday_orchestrator = FRIDAYOrchestrator()
