import os
import sys

from unittest.mock import AsyncMock, patch

import httpx
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.url_utils import sanitize_endpoint
from app.models.ollama_provider import OllamaProvider


def test_sanitize_endpoint_removes_credentials_path_and_query():
    assert sanitize_endpoint("https://user:pass@example.com:11434/api?token=secret") == (
        "https://example.com:11434"
    )


def test_sanitize_endpoint_keeps_local_origin():
    assert sanitize_endpoint("http://localhost:11434") == "http://localhost:11434"


@pytest.mark.asyncio
async def test_provider_health_does_not_expose_configured_url_credentials():
    provider = OllamaProvider(base_url="http://user:password@localhost:11434?token=secret")
    with patch(
        "httpx.AsyncClient.get",
        new=AsyncMock(side_effect=httpx.ConnectError("offline"))
    ):
        health = await provider.check_health()

    assert health.base_url == "http://localhost:11434"
    assert "password" not in health.error
    assert "secret" not in health.error
