from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from localmind.core.settings import Settings
from localmind.indexing.database import Database
from localmind.search.engine import SemanticSearchEngine
from localmind.search.saved import SavedSearchService


class SaveSearchRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    query: str = Field(min_length=1)
    repository_id: int | None = None
    min_score: float = Field(default=0.2, ge=0.0, le=1.0)
    result_limit: int = Field(default=10, ge=1, le=50)


class SavedSearchResponse(BaseModel):
    id: int
    name: str
    query: str
    repository_id: int | None
    min_score: float
    result_limit: int
    created_at: str


def build_saved_search_router(database: Database, settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/search/saved", tags=["search"])
    engine = SemanticSearchEngine(settings)

    @router.post("", response_model=SavedSearchResponse)
    async def save_search(payload: SaveSearchRequest) -> SavedSearchResponse:
        async with database.session() as session:
            service = SavedSearchService(session, engine)
            snapshot = await service.save(
                payload.name,
                payload.query,
                payload.repository_id,
                payload.min_score,
                payload.result_limit,
            )
            await session.commit()
        return SavedSearchResponse(**snapshot.__dict__)

    @router.get("", response_model=list[SavedSearchResponse])
    async def list_saved_searches(
        repository_id: int | None = Query(default=None),
    ) -> list[SavedSearchResponse]:
        async with database.session() as session:
            service = SavedSearchService(session, engine)
            records = await service.store.list_all(repository_id)
            snapshots = [service.store.snapshot(record) for record in records]
        return [SavedSearchResponse(**item.__dict__) for item in snapshots]

    @router.post("/{search_id}/run")
    async def run_saved_search(search_id: int) -> dict[str, object]:
        async with database.session() as session:
            service = SavedSearchService(session, engine)
            try:
                payload = await service.run_saved(search_id)
            except ValueError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
        return payload

    @router.get("/export")
    async def export_saved_searches(
        repository_id: int | None = Query(default=None),
    ) -> PlainTextResponse:
        async with database.session() as session:
            service = SavedSearchService(session, engine)
            payload = await service.export_json(repository_id)
        return PlainTextResponse(payload, media_type="application/json")

    @router.delete("/{search_id}")
    async def delete_saved_search(search_id: int) -> dict[str, bool]:
        async with database.session() as session:
            service = SavedSearchService(session, engine)
            deleted = await service.store.delete(search_id)
            await session.commit()
        if not deleted:
            raise HTTPException(status_code=404, detail="Saved search not found")
        return {"deleted": True}

    return router
