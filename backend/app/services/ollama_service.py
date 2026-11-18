import httpx
from app.config import settings
import re
import logging
import asyncio
from typing import Dict, Any, List, Optional
from app.core.url_utils import sanitize_endpoint
from app.services.voice_service import voice_service
from app.services.weather_service import weather_service
from app.services.search_service import search_service
from app.services.worldmonitor_service import world_monitor_service

logger = logging.getLogger(__name__)

class OllamaService:
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT_SECONDS
        self.retry_count = settings.OLLAMA_RETRY_COUNT

    def get_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self.timeout)

    async def check_health(self) -> Dict[str, Any]:
        """
        Quick diagnostic check to verify Ollama availability and model status.
        """
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    model_match = any(self.model in m for m in models)
                    return {
                        "connected": True,
                        "base_url": sanitize_endpoint(self.base_url),
                        "configured_model": self.model,
                        "model_available": model_match,
                        "installed_models": models,
                        "error": None if model_match else f"Configured model '{self.model}' not found in installed Ollama models"
                    }
                else:
                    return {
                        "connected": False,
                        "base_url": sanitize_endpoint(self.base_url),
                        "configured_model": self.model,
                        "model_available": False,
                        "installed_models": [],
                        "error": f"Ollama returned HTTP status {res.status_code}"
                    }
        except httpx.ConnectError:
            return {
                "connected": False,
                "base_url": sanitize_endpoint(self.base_url),
                "configured_model": self.model,
                "model_available": False,
                "installed_models": [],
                "error": "Cannot connect to Ollama (connection refused)"
            }
        except Exception as e:
            return {
                "connected": False,
                "base_url": sanitize_endpoint(self.base_url),
                "configured_model": self.model,
                "model_available": False,
                "installed_models": [],
                "error": f"Ollama health check failed ({type(e).__name__})"
            }

    async def raw_generate(self, prompt: str, system_prompt: str = None) -> str:
        """
        Generates a direct response from Ollama with retries and explicit error classification.
        """
        sys_prompt = system_prompt or "You are FRIDAY, a helpful assistant."
        payload = {
            "model": self.model,
            "prompt": f"System: {sys_prompt}\nUser: {prompt}\nFriday:",
            "stream": False,
            "options": {
                "temperature": 0.5
            }
        }
        
        last_error = None
        for attempt in range(self.retry_count + 1):
            try:
                async with self.get_client() as client:
                    response = await client.post(f"{self.base_url}/api/generate", json=payload)
                    if response.status_code == 200:
                        return response.json().get("response", "").strip()
                    elif response.status_code == 404:
                        logger.error(f"Ollama model '{self.model}' not found (HTTP 404).")
                        return ""
                    else:
                        logger.warning(f"Ollama generate returned status {response.status_code} on attempt {attempt + 1}")
            except httpx.ConnectError:
                logger.error("Cannot connect to Ollama server")
                last_error = "Ollama connection refused"
                break
            except httpx.TimeoutException:
                logger.warning("Ollama inference timeout on attempt %s", attempt + 1)
                last_error = "Ollama inference timed out"
                if attempt < self.retry_count:
                    await asyncio.sleep(1.0)
            except Exception as e:
                logger.error(
                    "Ollama raw generation failed on attempt %s (%s)",
                    attempt + 1,
                    type(e).__name__
                )
                last_error = f"Ollama generation failed ({type(e).__name__})"
                if attempt < self.retry_count:
                    await asyncio.sleep(0.5)

        logger.error(f"raw_generate failed after retries. Last error: {last_error}")
        return ""

    def detect_world_intent(self, text: str) -> bool:
        """
        Detects if the user's text relates to world news, geopolitics, conflicts,
        global statistics, or explicitly asks for the world monitor.
        """
        text_lower = text.lower()
        
        if any(trigger in text_lower for trigger in ["world monitor", "world dashboard", "global map", "situation map"]):
            return True
            
        keywords = [
            r"\bworld\b", r"\bglobal\b", r"\bgeopolitics?\b", r"\bconflict\b",
            r"\bwar(s)?\b", r"\bnews\b", r"\bearthquake(s)?\b", r"\bprotest(s)?\b",
            r"\binflation\b", r"\bgdp\b", r"\bmarkets?\b", r"\bworld problems\b",
            r"\bdisasters?\b", r"\bmilitary\b", r"\bships?\b", r"\baircraft\b",
            r"\blatest\b", r"\bcurrent\b", r"\btoday\b", r"\bdevelopments?\b"
        ]
        
        matches = [re.search(kw, text_lower) for kw in keywords]
        return any(matches)

    def detect_greeting(self, text: str) -> bool:
        """
        Detects if the user prompt is a greeting.
        """
        text_lower = text.lower()
        greetings = [r"\bhello\b", r"\bhi\b", r"\bhey\b", r"\bgood morning\b", r"\bgood afternoon\b", r"\bgreetings\b"]
        return any(re.search(g, text_lower) for g in greetings)

    def optimize_search_query(self, text: str) -> str:
        """
        Strips conversational filler and extracts key terms to prevent Google News RSS 
        from returning zero results on long natural language questions.
        """
        q = text.lower()
        q = q.replace("tams", "teams")
        
        clutter = [
            r"\bwhich\b", r"\bteams?\b", r"\bare\b", r"\bbeing\b", r"\bplaying\b",
            r"\bagainst\b", r"\band\b", r"\balso\b", r"\btell\b", r"\bme\b", r"\babout\b",
            r"\bwhat\b", r"\bshow\b", r"\bwho\b", r"\bhow\b", r"\bplease\b", r"\bthe\b", r"\bof\b",
            r"\bgoal\b", r"\bscore\b", r"\bsheet\b", r"\bsheets?\b", r"\bscores?\b", r"\bcan\b", r"\byou\b"
        ]
        
        for term in clutter:
            q = re.sub(term, "", q)
            
        q = re.sub(r'[?!\.,:;\(\)]', '', q)
        q = re.sub(r'\s+', ' ', q).strip()
        
        if not q:
            return text
            
        if "fifa" in q and ("worldcup" in q or "world cup" in q or "cup" in q):
            return "FIFA World Cup 2026 matches scores today"
            
        return q

    async def generate_response(self, prompt: str, history: list = None, system_prompt: str = None) -> dict:
        """
        Generates a response following the routing rules:
        1. World Monitor Query -> Answer from World Monitor app telemetry.
        2. News/Sports Query -> Perform web search, answer using latest facts.
        3. Other general query -> Draft answer with Ollama, verify/recheck via web search, provide corrected response.
        """
        import datetime
        prompt_lower = prompt.lower()
        
        wants_weather = any(w in prompt_lower for w in ["weather", "temperature", "temp", "forecast", "climate", "outside"])
        wants_location = any(w in prompt_lower for w in ["location", "where am i", "my city", "current position", "where i am", "which city", "what city"])
        wants_local_info = wants_weather or wants_location
        is_greeting = self.detect_greeting(prompt)
        
        hour = datetime.datetime.now().hour
        if 5 <= hour < 12:
            time_greeting = "Good morning Boss."
        elif 12 <= hour < 17:
            time_greeting = "Good afternoon Boss."
        elif 17 <= hour < 22:
            time_greeting = "Good evening Boss."
        else:
            time_greeting = "Greetings Boss. You're awake late at night today. What you up to?"

        is_initial = True
        if history:
            for msg in history:
                role = getattr(msg, "role", None)
                if role is None and isinstance(msg, dict):
                    role = msg.get("role")
                if role == "user":
                    is_initial = False
                    break

        if is_initial and is_greeting:
            weather = await weather_service.get_local_weather()
            weather_summary = (
                f"In {weather['city']} it is currently {weather['temp']} degrees Celsius with {weather['desc']}."
                if weather.get("temp") is not None
                else "Live local weather data is unavailable; do not infer current conditions."
            )
            default_system = (
                "You are FRIDAY (Female Real-time Intelligence Device & Assistant Yard), "
                "a highly sophisticated AI assistant inspired by Tony Stark's assistant in Iron Man. "
                "The user's name is Allen. You must greet him warmly by name as 'Allen', 'Boss', or 'Sir' in a soft, welcoming tone. "
                f"Use this exact dynamic time-of-day greeting: '{time_greeting}' "
                f"{weather_summary} "
                "After the weather introduction, answer his query concisely. Speak in a sleek, confident tone."
            )
        else:
            default_system = (
                "You are FRIDAY (Female Real-time Intelligence Device & Assistant Yard), "
                "a highly sophisticated AI assistant inspired by Tony Stark's assistant in Iron Man. "
                "Respond in a soft, sleek, intelligent, confident, and professional tone. "
                "The user's name is Allen. Address him as Allen, Boss, or Sir. Avoid repeating greetings or weather reports "
                "unless specifically asked. Keep replies direct, helpful, and concise."
            )
        sys_prompt = system_prompt or default_system

        # Route 1: World Monitor
        from app.services.agent_service import agent_service
        is_wm = agent_service.is_world_monitor_telemetry_query(prompt)
        
        wm_keywords = [
            "world monitor", "world dashboard", "situation map", "global map",
            "world news", "global news", "world events", "geopolitical news",
            "international news", "latest world news", "world updates",
            "happening in the world", "happening around the world",
            "conflict", "clash", "protest", "civil unrest", "military activity", "troop movement", "flight tracker", "naval position", "risk index", "instability", "security threat", "threat matrix", "active conflict", "geopolitical risk", "risk score", "global risk index", "active hotzone",
            "undersea cable", "pipeline", "nuclear facility", "airport", "shipping port", "ai data center", "tech hub", "cloud region", "botnet", "malware", "cyber threat", "internet outage", "tech monitor",
            "stock exchange", "commodity", "gold price", "oil price", "cryptocurrency", "inflation", "interest rate", "stablecoin", "etf", "fear and greed", "polymarket", "prediction market", "finance monitor",
            "energy flow", "petroleum reserve", "gas storage", "supply chain disruption", "port strike", "energy monitor", "commodity monitor",
            "earthquake", "volcano", "volcanic eruption", "wildfire", "nasa firms", "flood alert", "storm track", "environment tracking",
            "progress tracker", "scientific breakthrough", "renewable energy", "conservation win", "happy monitor",
            "world brief", "ai forecast", "threat probability", "scenario engine"
        ]
        
        if any(wk in prompt_lower for wk in wm_keywords):
            is_wm = True
            
        if "world" in prompt_lower and "happening" in prompt_lower:
            is_wm = True
            
        countries = [
            "myanmar", "ukraine", "pakistan", "mexico", "russia", "palestine", "israel", 
            "yemen", "syria", "somalia", "sudan", "venezuela", "afghanistan", "libya", 
            "iraq", "iran", "north korea", "taiwan", "china", "united states"
        ]
        conflict_terms = ["conflict", "war", "risk", "threat", "stability", "security", "safe", "advisory", "telemetry", "status", "situation", "hotzone", "tension", "unrest", "military", "clash"]
        has_country = any(c in prompt_lower for c in countries)
        has_conflict_term = any(ct in prompt_lower for ct in conflict_terms)
        if has_country and has_conflict_term:
            is_wm = True

        if wants_local_info:
            is_wm = False

        if is_wm:
            logger.info("Routing query to World Monitor path.")
            try:
                world_context = await world_monitor_service.get_world_summary_context()
            except Exception as e:
                logger.error("World Monitor context failed (%s)", type(e).__name__)
                world_context = "World Monitor service is currently unreachable."
            
            try:
                news_context = await world_monitor_service.get_world_news_context()
            except Exception as e:
                logger.error("World Monitor news context failed (%s)", type(e).__name__)
                news_context = "World news feed offline."
            
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
            response_text = await self.raw_generate(
                prompt=(
                    f"World Monitor Telemetry Data:\n{world_context}\n\n"
                    f"News Feed context (with publish dates and channel sources):\n{news_context}\n\n"
                    f"User request: {prompt}"
                ),
                system_prompt=wm_system_prompt
            )
            error_msg = None
            if not response_text:
                response_text = (
                    "Give me a sec, Boss. Let me check.\n\n"
                    f"Here is the telemetry context, Sir:\n{world_context}\n\n"
                    f"Latest World News Feed:\n{news_context}\n\n"
                    "Let me open up the world monitor so you can better visualize what's happening, Boss."
                )
                error_msg = f"Ollama connection offline or model '{self.model}' unavailable"
                
            voice_service.speak(response_text)
            return {
                "text": response_text,
                "trigger_dashboard": True,
                "error": error_msg
            }

        # Route 2: News / Sports
        is_news_sports = False
        news_sports_keywords = [
            "news", "sports", "match", "game", "win", "won", "play", "playing", 
            "score", "scores", "fifa", "cricket", "football", "baseball", 
            "basketball", "tennis", "olympics", "championship", "tournament", 
            "cup", "vs", "against", "headline", "headlines", "latest updates"
        ]
        if any(k in prompt_lower for k in news_sports_keywords):
            is_news_sports = True
            
        if wants_local_info:
            is_news_sports = False

        if is_news_sports:
            logger.info("Routing query to News/Sports path.")
            optimized_query = self.optimize_search_query(prompt)
            try:
                search_context = await search_service.search(optimized_query)
            except Exception as e:
                logger.error("News search failed (%s)", type(e).__name__)
                search_context = "No real-time search context could be retrieved for this query."
            
            news_system_prompt = (
                "You are FRIDAY (Female Real-time Intelligence Device & Assistant Yard), "
                "a highly sophisticated AI assistant inspired by Tony Stark's assistant in Iron Man. "
                "Answer the user's news or sports question using the provided search context. "
                "Address the user as Allen or Sir. Speak in a sleek, confident tone."
            )
            response_text = await self.raw_generate(
                prompt=f"Search Context:\n{search_context}\n\nUser request: {prompt}",
                system_prompt=news_system_prompt
            )
            error_msg = None
            if not response_text:
                response_text = f"I retrieved these news items regarding your query, Sir: {search_context}"
                error_msg = f"Ollama connection offline or model '{self.model}' unavailable"
            
            voice_service.speak(response_text)
            return {
                "text": response_text,
                "trigger_dashboard": False,
                "error": error_msg
            }

        # Route 3: General Queries
        logger.info("Routing query to General/Other path with verification check.")
        
        # Local weather/location
        if wants_local_info:
            weather = await weather_service.get_local_weather()
            if weather.get("temp") is None:
                city = weather.get("city", "your area")
                if wants_location and weather.get("location_available"):
                    response_text = f"Your approximate location is {city}, Sir. Live weather data is unavailable."
                else:
                    response_text = f"Live weather data is unavailable for {city}, Sir."
                voice_service.speak(response_text)
                return {
                    "text": response_text,
                    "trigger_dashboard": False,
                    "error": weather.get("status_message", "Live weather data is unavailable.")
                }

            local_info_context = (
                f"User's Current Location: {weather['city']}\n"
                f"User's Local Weather: {weather['temp']}°C, {weather['desc']}"
            )
            response_text = await self.raw_generate(
                prompt=f"Local Context:\n{local_info_context}\n\nUser request: {prompt}",
                system_prompt=sys_prompt
            )
            error_msg = None
            if not response_text:
                response_text = (
                    f"Telemetry sensor check: Location detected as {weather['city']}. "
                    f"Current temperature is {weather['temp']}°C with {weather['desc']}."
                )
                error_msg = f"Ollama connection offline or model '{self.model}' unavailable"
            voice_service.speak(response_text)
            return {
                "text": response_text,
                "trigger_dashboard": False,
                "error": error_msg
            }

        # Greetings
        if is_greeting:
            response_text = await self.raw_generate(prompt=prompt, system_prompt=sys_prompt)
            error_msg = None
            if not response_text:
                response_text = "Hello Allen. How can I assist you today, Sir?"
                error_msg = f"Ollama connection offline or model '{self.model}' unavailable"
            voice_service.speak(response_text)
            return {
                "text": response_text,
                "trigger_dashboard": False,
                "error": error_msg
            }

        # General queries: draft and verify
        draft_response = await self.raw_generate(prompt=prompt, system_prompt=sys_prompt)
        
        optimized_query = self.optimize_search_query(prompt)
        verification_query = f"{optimized_query} verification fact check"
        try:
            verification_facts = await search_service.search(verification_query)
        except Exception as e:
            logger.error("Search verification failed (%s)", type(e).__name__)
            verification_facts = "Verification facts unavailable."

        verification_system_prompt = (
            "You are FRIDAY (Female Real-time Intelligence Device & Assistant Yard), "
            "a highly sophisticated AI assistant inspired by Tony Stark's assistant in Iron Man. "
            "You are given a DRAFT response to a user's question, and search results containing verification facts. "
            "Your job is to double-check the DRAFT response against the verification facts: "
            "1. Identify any factual errors, contradictions, outdated stats, or hallucinations in the draft response. "
            "2. Correct them based strictly on the verification facts. "
            "3. If the draft response is accurate, maintain its contents but refine the tone. "
            "4. Output the final correct response in a soft, sleek, professional voice addressing the user as Allen or Sir. "
            "Do not mention 'draft response', 'verification facts', or 'corrections' in your final answer. Just present the polished, final response."
        )
        
        final_verified_response = None
        error_msg = None
        if draft_response:
            final_verified_response = await self.raw_generate(
                prompt=(
                    f"User Request: {prompt}\n\n"
                    f"Draft Response: {draft_response}\n\n"
                    f"Verification Facts:\n{verification_facts}"
                ),
                system_prompt=verification_system_prompt
            )
        
        if not final_verified_response:
            final_verified_response = (
                "Diagnostic mode active, Allen. Establishing connection to my core LLM engine is currently delayed. "
                "Subsystems are functional. "
            )
            if verification_facts and verification_facts != "Verification facts unavailable.":
                final_verified_response += f"I retrieved these search results: {verification_facts}"
            error_msg = f"Ollama connection offline or model '{self.model}' unavailable"

        voice_service.speak(final_verified_response)
        return {
            "text": final_verified_response,
            "trigger_dashboard": False,
            "error": error_msg
        }

ollama_service = OllamaService()
