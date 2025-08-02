import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from localmind.core.settings import Settings
from localmind.rag.chunker import ContextChunker
from localmind.rag.models import ChatMessage
from localmind.rag.prompts import PromptBuilder
from localmind.rag.service import RepositoryChatService
from localmind.search.models import SearchResult


def test_context_chunker_truncates_large_snippets() -> None:
    chunker = ContextChunker()
    results = [
        SearchResult(
            entity_id="1:1",
            score=0.9,
            file_path="big.py",
            start_line=1,
            end_line=200,
            entity_type="function",
            snippet="x" * 2000,
            repository_id=1,
        )
    ]
    chunks = chunker.build_chunks(results)
    assert len(chunks[0].content) == chunker.MAX_CHUNK_CHARS


def test_prompt_builder_includes_context() -> None:
    builder = PromptBuilder()
    messages = builder.build(
        "Where is jwt auth implemented?",
        "auth.py::verify_jwt",
        history=[ChatMessage(role="user", content="previous")],
    )
    assert messages[0].role == "system"
    assert "jwt auth" in messages[-1].content.lower()


@pytest.mark.asyncio
async def test_repository_chat_service_ask(settings: Settings | None = None) -> None:
    service = RepositoryChatService(Settings(data_dir=Path("/tmp/localmind-test")))
    service.search_engine = MagicMock()
    service.search_engine.search.return_value = [
        SearchResult(
            entity_id="1:1",
            score=0.95,
            file_path="auth.py",
            start_line=4,
            end_line=18,
            entity_type="function",
            snippet="def verify_jwt(token): ...",
            repository_id=1,
        )
    ]
    service.ollama = AsyncMock()
    service.ollama.chat.return_value = "JWT verification lives in auth.py."

    result = await service.ask("Where is JWT authentication implemented?", repository_id=1)
    assert "JWT" in result["answer"]
    assert result["citations"]
