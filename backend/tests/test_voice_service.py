import os
import sys
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.voice_service import VoiceService


def test_server_voice_is_not_started_when_disabled():
    with patch("app.services.voice_service.threading.Thread") as thread:
        VoiceService(enabled=False).speak("A response")

    thread.assert_not_called()


def test_server_voice_starts_worker_when_enabled():
    worker = Mock()
    with patch(
        "app.services.voice_service.threading.Thread",
        return_value=worker
    ) as thread:
        VoiceService(enabled=True).speak("A response")

    thread.assert_called_once()
    worker.start.assert_called_once()
