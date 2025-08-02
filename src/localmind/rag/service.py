from collections.abc import AsyncIterator

from localmind.core.settings import Settings
from localmind.rag.chunker import ContextChunker
from localmind.rag.models import ChatMessage
from localmind.rag.ollama import OllamaClient
from localmind.rag.prompts import PromptBuilder
from localmind.search.engine import SemanticSearchEngine


class RepositoryChatService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.search_engine = SemanticSearchEngine(settings)
        self.chunker = ContextChunker()
        self.prompt_builder = PromptBuilder()
        self.ollama = OllamaClient(settings)

    async def ask(
        self,
        question: str,
        repository_id: int | None = None,
        history: list[ChatMessage] | None = None,
    ) -> dict[str, object]:
        search_results = self.search_engine.search(question, repository_id=repository_id, limit=8)
        chunks = self.chunker.build_chunks(search_results)
        context = self.chunker.merge_chunks(chunks)
        messages = self.prompt_builder.build(question, context, history=history)
        answer = await self.ollama.chat(messages)
        return {
            "question": question,
            "answer": answer,
            "citations": self.prompt_builder.citations(chunks),
        }

    async def stream(
        self,
        question: str,
        repository_id: int | None = None,
        history: list[ChatMessage] | None = None,
    ) -> AsyncIterator[str]:
        search_results = self.search_engine.search(question, repository_id=repository_id, limit=8)
        chunks = self.chunker.build_chunks(search_results)
        context = self.chunker.merge_chunks(chunks)
        messages = self.prompt_builder.build(question, context, history=history)
        prompt = self.prompt_builder.format_for_ollama(messages)
        async for token in self.ollama.stream(prompt):
            yield token
