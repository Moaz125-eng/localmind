from fastapi import APIRouter
from pydantic import BaseModel, Field

from localmind.core.settings import Settings
from localmind.rag.runtime import OllamaRuntime


class OllamaModelResponse(BaseModel):
    name: str
    size_bytes: int
    modified_at: str


class OllamaHealthResponse(BaseModel):
    reachable: bool
    base_url: str
    configured_model: str
    model_available: bool
    model_count: int
    error: str | None = None


class PullModelRequest(BaseModel):
    model_name: str = Field(min_length=1)


def build_runtime_router(settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/runtime", tags=["runtime"])
    runtime = OllamaRuntime(settings)

    @router.get("/ollama/health", response_model=OllamaHealthResponse)
    async def ollama_health() -> OllamaHealthResponse:
        status = await runtime.health()
        return OllamaHealthResponse(
            reachable=status.reachable,
            base_url=status.base_url,
            configured_model=status.configured_model,
            model_available=status.model_available,
            model_count=status.model_count,
            error=status.error,
        )

    @router.get("/ollama/models", response_model=list[OllamaModelResponse])
    async def ollama_models() -> list[OllamaModelResponse]:
        models = await runtime.list_models()
        return [
            OllamaModelResponse(
                name=model.name,
                size_bytes=model.size_bytes,
                modified_at=model.modified_at,
            )
            for model in models
        ]

    @router.post("/ollama/pull")
    async def pull_ollama_model(payload: PullModelRequest) -> dict[str, object]:
        return await runtime.pull_model(payload.model_name)

    return router
