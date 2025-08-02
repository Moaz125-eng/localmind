from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from localmind.core.settings import Settings
from localmind.rag.models import ChatMessage
from localmind.rag.service import RepositoryChatService


class ChatHistoryItem(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    repository_id: int | None = None
    history: list[ChatHistoryItem] = Field(default_factory=list)


class CitationResponse(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    score: float


class ChatResponse(BaseModel):
    question: str
    answer: str
    citations: list[CitationResponse]


def build_chat_router(settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/chat", tags=["chat"])
    service = RepositoryChatService(settings)

    @router.post("", response_model=ChatResponse)
    async def chat(payload: ChatRequest) -> ChatResponse:
        history = [ChatMessage(role=item.role, content=item.content) for item in payload.history]
        result = await service.ask(payload.question, repository_id=payload.repository_id, history=history)
        citations = [
            CitationResponse(
                file_path=str(item["file_path"]),
                start_line=int(item["start_line"]),
                end_line=int(item["end_line"]),
                score=float(item["score"]),
            )
            for item in result["citations"]
        ]
        return ChatResponse(
            question=str(result["question"]),
            answer=str(result["answer"]),
            citations=citations,
        )

    @router.post("/stream")
    async def chat_stream(payload: ChatRequest) -> StreamingResponse:
        history = [ChatMessage(role=item.role, content=item.content) for item in payload.history]

        async def event_stream():
            async for token in service.stream(
                payload.question,
                repository_id=payload.repository_id,
                history=history,
            ):
                yield token

        return StreamingResponse(event_stream(), media_type="text/plain")

    return router
