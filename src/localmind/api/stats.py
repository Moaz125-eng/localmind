from fastapi import APIRouter, HTTPException

from localmind.indexing.database import Database
from localmind.indexing.stats import RepositoryStatsService


def build_stats_router(database: Database) -> APIRouter:
    router = APIRouter(prefix="/stats", tags=["stats"])

    @router.get("/summary")
    async def global_stats() -> dict[str, int]:
        async with database.session() as session:
            service = RepositoryStatsService(session)
            return await service.global_summary()

    @router.get("/repositories/{repository_id}")
    async def repository_stats(repository_id: int) -> dict[str, int | str | None]:
        async with database.session() as session:
            service = RepositoryStatsService(session)
            try:
                return await service.summary(repository_id)
            except ValueError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.get("/repositories/{repository_id}/snapshot")
    async def export_snapshot(repository_id: int) -> dict[str, object]:
        from localmind.indexing.snapshot import SnapshotExporter
        import json

        async with database.session() as session:
            exporter = SnapshotExporter(session)
            try:
                snapshot = await exporter.export(repository_id)
            except ValueError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            payload = json.loads(exporter.to_json(snapshot))
        return payload

    return router
