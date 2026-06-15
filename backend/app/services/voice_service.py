import pyttsx3
import threading
import logging
import re

logger = logging.getLogger(__name__)

class VoiceService:
    def __init__(self):
        pass

    def _speak_worker(self, text: str):
        try:
            # On Windows, COM must be initialized for each new thread to support SAPI5 (pyttsx3)
            try:
                import pythoncom
                pythoncom.CoInitialize()
            except ImportError:
                logger.warning("pythoncom not found; running TTS without manual COM initialization.")

            # Initialize engine in the thread context
            engine = pyttsx3.init()
            
            # Configure rate and volume for a natural, fluent tone
            engine.setProperty('rate', 175)  # Natural human reading speed
            engine.setProperty('volume', 0.95)
            
            # Look for a female voice registry
            voices = engine.getProperty('voices')
            female_voice = None
            
            for voice in voices:
                vname = voice.name.lower()
                if any(name in vname for name in ["zira", "female", "hazel", "helen"]):
                    female_voice = voice.id
                    break
            
            if female_voice:
                engine.setProperty('voice', female_voice)
            else:
                if len(voices) > 1:
                    engine.setProperty('voice', voices[1].id)
            
            # Run speaking task
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            logger.error(f"Voice speech thread crashed: {e}")

    def speak(self, text: str):
        """
        Executes text-to-speech in a background thread so the FastAPI response 
        returns instantly while the computer starts speaking.
        """
        if not text:
            return
            
        # 1. Strip markdown characters (*, _, #, `, -)
        clean_text = re.sub(r'[*#`_\-]', ' ', text)
        
        # 2. Strip search citations (e.g. [1], [2]) which sound robotic
        clean_text = re.sub(r'\[\d+\]', '', clean_text)
        
        # 3. Replace double hyphens or arrows
        clean_text = clean_text.replace("->", " leads to ").replace("=>", " equals ")
        
        # 4. Replace newlines with spaces and merge extra whitespace
        clean_text = clean_text.replace('\n', ' ')
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        # Start background worker thread
        t = threading.Thread(target=self._speak_worker, args=(clean_text,), daemon=True)
        t.start()

voice_service = VoiceService()
