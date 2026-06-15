import logging
from typing import Dict, Any, List
from app.services.worldmonitor_service import world_monitor_service
from app.services.search_service import search_service
from app.services.voice_service import voice_service

logger = logging.getLogger(__name__)

class AgentService:
    def is_world_monitor_telemetry_query(self, prompt: str) -> bool:
        """
        Detects if the query is specifically asking for global risk scores, threat matrix,
        or monitored hotzones from the World Monitor.
        """
        p_lower = prompt.lower()
        triggers = [
            "global risk", "risk index", "risk score", "threat matrix",
            "active hotzone", "monitored hotzone", "active conflict",
            "telemetry", "world monitor index", "world monitor stats",
            "world monitor telemetry", "threat score", "gdp ranking",
            "world news", "global news", "world events", "geopolitical news",
            "international news", "latest world news", "world updates",
            "happening in the world", "happening around the world"
        ]
        if any(t in p_lower for t in triggers):
            return True
        if "world" in p_lower and "happening" in p_lower:
            return True
        return False

    async def run_agent_pipeline(self, prompt: str, history: List[Any] = None) -> Dict[str, Any]:
        """
        Runs the multi-agent routing, search, and verification pipeline.
        """
        # We import ollama_service locally to avoid circular dependencies
        from app.services.ollama_service import ollama_service

        logger.info(f"Agent Pipeline triggered for query: '{prompt}'")

        # 1. Check if this query can be directly answered by World Monitor telemetry data
        if self.is_world_monitor_telemetry_query(prompt):
            logger.info("Routing query to World Monitor shortcut path.")
            try:
                world_context = await world_monitor_service.get_world_summary_context()
            except Exception as e:
                logger.error(f"Error fetching world monitor context: {e}")
                world_context = "World Monitor service is currently unreachable."

            system_prompt = (
                "You are FRIDAY (Female Real-time Intelligence Device & Assistant Yard), "
                "a highly sophisticated AI assistant inspired by Tony Stark's assistant in Iron Man. "
                "The user's name is Allen. You must present the global threat matrix, risk indices, "
                "or monitored hotzones clearly and concisely based ONLY on the provided World Monitor telemetry. "
                "Do not fetch news or run web search verification. Speak in a sleek, confident tone."
            )
            
            # Use raw generate to avoid looping back to the agent pipeline
            summarized_response = await ollama_service.raw_generate(
                prompt=f"World Monitor Telemetry Data:\n{world_context}\n\nUser request: {prompt}",
                system_prompt=system_prompt
            )

            # Fallback if Ollama raw generate failed
            if not summarized_response:
                summarized_response = (
                    f"Here is the telemetry context, Sir:\n{world_context}\n"
                    "I am currently operating under localized offline diagnostics."
                )

            # Trigger voice playback
            voice_service.speak(summarized_response)

            return {
                "text": summarized_response,
                "trigger_dashboard": True,
                "error": None
            }

        # 2. General latest/real-time query: Execute full verification loop
        logger.info("Executing full verification pipeline.")

        # Step A: World Monitor Agent (Background Context)
        try:
            world_context = await world_monitor_service.get_world_summary_context()
        except Exception as e:
            logger.error(f"Error fetching world monitor context: {e}")
            world_context = "World Monitor offline."

        # Step B: News Agent (Fetch news headlines)
        # Strip conversational filler to search effectively
        optimized_query = ollama_service.optimize_search_query(prompt)
        try:
            news_context = await search_service.search(optimized_query)
        except Exception as e:
            logger.error(f"Error fetching news context: {e}")
            news_context = "News search feed offline."

        # Combine context for Drafting
        combined_draft_context = (
            f"World Monitor Risk Telemetry:\n{world_context}\n\n"
            f"News feed results:\n{news_context}"
        )

        draft_system_prompt = (
            "You are FRIDAY, a highly sophisticated AI assistant. "
            "Write a DRAFT answer to the user's question using the provided news and telemetry context. "
            "Address the user as Allen or Sir. Keep the draft response direct and clear."
        )

        # Step C: Generate Draft Answer
        logger.info("Generating draft response...")
        draft_response = await ollama_service.raw_generate(
            prompt=f"Context:\n{combined_draft_context}\n\nUser request: {prompt}",
            system_prompt=draft_system_prompt
        )

        if not draft_response:
            draft_response = f"I retrieved these news items regarding your query, Sir: {news_context}"

        logger.info(f"Draft Response: {draft_response}")

        # Step D: Search Agent Verification
        # Query search engine using the draft response key terms or user query + verification keywords
        verification_query = f"{optimized_query} verification fact check"
        logger.info(f"Running Search Agent verification query: '{verification_query}'")
        try:
            verification_facts = await search_service.search(verification_query)
        except Exception as e:
            logger.error(f"Search Agent verification failed: {e}")
            verification_facts = "Verification facts unavailable."

        # Step E: Verification / Correction Agent (Self-Correction)
        verification_system_prompt = (
            "You are FRIDAY, a highly sophisticated AI assistant. "
            "You are given a DRAFT response to a user's question, and search results containing verification facts. "
            "Your job is to double-check the DRAFT response against the verification facts: "
            "1. Identify any factual errors, contradictions, outdated stats, or hallucinations in the draft response. "
            "2. Correct them based strictly on the verification facts. "
            "3. If the draft response is accurate, maintain its contents but refine the tone. "
            "4. Output the final correct response in a soft, sleek, professional voice addressing the user as Allen or Sir. "
            "Do not mention 'draft response', 'verification facts', or 'corrections' in your final answer. Just present the polished, final response."
        )

        logger.info("Running verification and self-correction...")
        final_verified_response = await ollama_service.raw_generate(
            prompt=(
                f"User Request: {prompt}\n\n"
                f"Draft Response: {draft_response}\n\n"
                f"Verification Facts:\n{verification_facts}"
            ),
            system_prompt=verification_system_prompt
        )

        # Fallback if verification generation fails
        if not final_verified_response:
            final_verified_response = draft_response

        # Trigger voice playback
        voice_service.speak(final_verified_response)

        return {
            "text": final_verified_response,
            "trigger_dashboard": True,
            "error": None
        }

agent_service = AgentService()
