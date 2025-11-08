from unittest.mock import AsyncMock, MagicMock

import pytest

from localmind.core.settings import Settings
from localmind.rag.runtime import OllamaHealthStatus, OllamaModelInfo, OllamaRuntime


@pytest.mark.asyncio
async def test_ollama_health_when_models_available() -> None:
    runtime = OllamaRuntime(Settings(ollama_model="llama3.2"))
    runtime.list_models = AsyncMock(
        return_value=[
            OllamaModelInfo(name="llama3.2:latest", size_bytes=1000, modified_at="today"),
        ]
    )
    status = await runtime.health()
    assert status.reachable is True
    assert status.model_available is True
    assert status.model_count == 1


@pytest.mark.asyncio
async def test_ollama_health_when_unreachable() -> None:
    runtime = OllamaRuntime(Settings())
    runtime.list_models = AsyncMock(side_effect=ConnectionError("offline"))
    status = await runtime.health()
    assert status.reachable is False
    assert status.error is not None


@pytest.mark.asyncio
async def test_ollama_list_models_parses_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = OllamaRuntime(Settings())

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "models": [
                    {"name": "llama3.2", "size": 2048, "modified_at": "2025-11-01"},
                ]
            }

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url: str):
            return FakeResponse()

    monkeypatch.setattr("localmind.rag.runtime.httpx.AsyncClient", lambda **kwargs: FakeClient())
    models = await runtime.list_models()
    assert models[0].name == "llama3.2"
