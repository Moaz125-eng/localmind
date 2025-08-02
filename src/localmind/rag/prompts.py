from localmind.rag.models import ChatMessage, RetrievedChunk


class PromptBuilder:
    SYSTEM_PROMPT = (
        "You are LocalMind, a repository assistant. "
        "Answer using only the provided code context. "
        "Reference file paths and line ranges when helpful."
    )

    def build(self, question: str, context: str, history: list[ChatMessage] | None = None) -> list[ChatMessage]:
        messages: list[ChatMessage] = [ChatMessage(role="system", content=self.SYSTEM_PROMPT)]
        if history:
            messages.extend(history[-4:])
        user_content = (
            f"Question:\n{question}\n\n"
            f"Repository context:\n{context if context else 'No relevant context found.'}"
        )
        messages.append(ChatMessage(role="user", content=user_content))
        return messages

    def format_for_ollama(self, messages: list[ChatMessage]) -> str:
        parts: list[str] = []
        for message in messages:
            parts.append(f"{message.role.upper()}:\n{message.content}")
        parts.append("ASSISTANT:")
        return "\n\n".join(parts)

    def citations(self, chunks: list[RetrievedChunk]) -> list[dict[str, object]]:
        return [
            {
                "file_path": chunk.file_path,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "score": chunk.score,
            }
            for chunk in chunks
        ]
