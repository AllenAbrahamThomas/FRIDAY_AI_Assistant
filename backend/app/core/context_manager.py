import datetime
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class ContextManager:
    """
    Manages session context, dynamic Iron Man-style greetings, and synthesis prompt generation.
    """

    def get_time_greeting(self) -> str:
        hour = datetime.datetime.now().hour
        if 5 <= hour < 12:
            return "Good morning Boss."
        elif 12 <= hour < 17:
            return "Good afternoon Boss."
        elif 17 <= hour < 22:
            return "Good evening Boss."
        else:
            return "Greetings Boss. You're awake late at night today. What you up to?"

    def build_system_prompt(self, is_initial: bool = False, is_greeting: bool = False) -> str:
        time_greeting = self.get_time_greeting()
        if is_initial and is_greeting:
            return (
                "You are FRIDAY (Female Real-time Intelligence Device & Assistant Yard), "
                "a highly sophisticated AI assistant inspired by Tony Stark's assistant in Iron Man. "
                "The user's name is Allen. You must greet him warmly by name as 'Allen', 'Boss', or 'Sir' in a soft, welcoming tone. "
                f"Use this exact dynamic time-of-day greeting: '{time_greeting}' "
                "Speak in a sleek, confident, professional tone."
            )
        else:
            return (
                "You are FRIDAY (Female Real-time Intelligence Device & Assistant Yard), "
                "a highly sophisticated AI assistant inspired by Tony Stark's assistant in Iron Man. "
                "Respond in a soft, sleek, intelligent, confident, and professional tone. "
                "The user's name is Allen. Address him as Allen, Boss, or Sir. "
                "Keep replies direct, helpful, and concise."
            )

    def build_synthesis_prompt(
        self,
        prompt: str,
        observations: List[Dict[str, Any]],
        intent: str
    ) -> str:
        """
        Combines tool observations into a structured context for model synthesis.
        """
        obs_blocks = []
        for obs in observations:
            tool_name = obs.get("tool_name", "Tool")
            data = obs.get("data")
            error = obs.get("error")
            if error:
                obs_blocks.append(f"[{tool_name}]: Failed ({error})")
            elif isinstance(data, dict):
                if "summary_context" in data:
                    obs_blocks.append(f"[{tool_name} Telemetry]:\n{data['summary_context']}")
                elif "news_context" in data:
                    obs_blocks.append(f"[{tool_name} News Digest]:\n{data['news_context']}")
                else:
                    obs_blocks.append(f"[{tool_name}]:\n{data}")
            else:
                obs_blocks.append(f"[{tool_name} Observation]:\n{data}")

        collected_context = "\n\n---\n\n".join(obs_blocks)
        return (
            f"Observed Intelligence Context:\n{collected_context}\n\n"
            f"User Request: {prompt}"
        )

context_manager = ContextManager()
