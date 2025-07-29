from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from localmind.core.settings import Settings
from localmind.embeddings.pipeline import EmbeddingPipeline
from localmind.indexing.database import Database
from localmind.indexing.store import IndexStore


class EmbedRepositoryResponse(BaseModel):
    repository_id: int
    embedded: int
    cached: int
    vector_count: int


def build_embedding_router(database: Database, settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/embeddings", tags=["embeddings"])

    @router.post("/repositories/{repository_id}", response_model=EmbedRepositoryResponse)
    async def embed_repository(repository_id: int) -> EmbedRepositoryResponse:
        async with database.session() as session:
            store = IndexStore(session)
            repository = await store.get_repository_by_id(repository_id)
            if repository is None:
                raise HTTPException(status_code=404, detail="Repository not found")
            pipeline = EmbeddingPipeline(settings, session)
            stats = await pipeline.embed_repository(repository_id)
            await session.commit()
            return EmbedRepositoryResponse(
                repository_id=repository_id,
                embedded=stats["embedded"],
                cached=stats["cached"],
                vector_count=pipeline.vector_store.count(),
            )

    return router
