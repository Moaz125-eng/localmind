from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from localmind.core.settings import Settings
from localmind.search.engine import SemanticSearchEngine
from localmind.search.models import SearchResult


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    repository_id: int | None = None
    limit: int = Field(default=10, ge=1, le=50)
    min_score: float = Field(default=0.2, ge=0.0, le=1.0)


class SearchResultResponse(BaseModel):
    entity_id: str
    score: float
    file_path: str
    start_line: int
    end_line: int
    entity_type: str
    snippet: str
    repository_id: int


class SearchResponse(BaseModel):
    query: str
    count: int
    results: list[SearchResultResponse]


def build_search_router(settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/search", tags=["search"])
    engine = SemanticSearchEngine(settings)

    def serialize(results: list[SearchResult]) -> list[SearchResultResponse]:
        return [
            SearchResultResponse(
                entity_id=item.entity_id,
                score=item.score,
                file_path=item.file_path,
                start_line=item.start_line,
                end_line=item.end_line,
                entity_type=item.entity_type,
                snippet=item.snippet,
                repository_id=item.repository_id,
            )
            for item in results
        ]

    @router.post("", response_model=SearchResponse)
    async def search_post(payload: SearchRequest) -> SearchResponse:
        results = engine.search(
            payload.query,
            repository_id=payload.repository_id,
            limit=payload.limit,
            min_score=payload.min_score,
        )
        return SearchResponse(query=payload.query, count=len(results), results=serialize(results))

    @router.get("", response_model=SearchResponse)
    async def search_get(
        query: str = Query(min_length=1),
        repository_id: int | None = None,
        limit: int = Query(default=10, ge=1, le=50),
        min_score: float = Query(default=0.2, ge=0.0, le=1.0),
    ) -> SearchResponse:
        results = engine.search(
            query,
            repository_id=repository_id,
            limit=limit,
            min_score=min_score,
        )
        return SearchResponse(query=query, count=len(results), results=serialize(results))

    return router
