import json
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from localmind.search.engine import SemanticSearchEngine
from localmind.search.models import SearchResult
from localmind.search.saved_models import SavedSearchRecord


@dataclass(frozen=True)
class SavedSearchSnapshot:
    id: int
    name: str
    query: str
    repository_id: int | None
    min_score: float
    result_limit: int
    created_at: str


class SavedSearchStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        name: str,
        query: str,
        repository_id: int | None,
        min_score: float,
        result_limit: int,
    ) -> SavedSearchRecord:
        record = SavedSearchRecord(
            name=name,
            query=query,
            repository_id=repository_id,
            min_score=int(min_score * 100),
            result_limit=result_limit,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def list_all(self, repository_id: int | None = None) -> list[SavedSearchRecord]:
        stmt = select(SavedSearchRecord).order_by(SavedSearchRecord.created_at.desc())
        if repository_id is not None:
            stmt = stmt.where(SavedSearchRecord.repository_id == repository_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get(self, search_id: int) -> SavedSearchRecord | None:
        result = await self.session.execute(
            select(SavedSearchRecord).where(SavedSearchRecord.id == search_id)
        )
        return result.scalar_one_or_none()

    async def delete(self, search_id: int) -> bool:
        record = await self.get(search_id)
        if record is None:
            return False
        await self.session.delete(record)
        await self.session.flush()
        return True

    def snapshot(self, record: SavedSearchRecord) -> SavedSearchSnapshot:
        return SavedSearchSnapshot(
            id=record.id,
            name=record.name,
            query=record.query,
            repository_id=record.repository_id,
            min_score=record.min_score / 100,
            result_limit=record.result_limit,
            created_at=record.created_at.isoformat(),
        )


class SavedSearchService:
    def __init__(self, session: AsyncSession, engine: SemanticSearchEngine) -> None:
        self.store = SavedSearchStore(session)
        self.engine = engine

    async def save(
        self,
        name: str,
        query: str,
        repository_id: int | None,
        min_score: float,
        result_limit: int,
    ) -> SavedSearchSnapshot:
        record = await self.store.create(name, query, repository_id, min_score, result_limit)
        return self.store.snapshot(record)

    async def run_saved(self, search_id: int) -> dict[str, object]:
        record = await self.store.get(search_id)
        if record is None:
            raise ValueError(f"Saved search {search_id} not found")
        results = self.engine.search(
            record.query,
            repository_id=record.repository_id,
            limit=record.result_limit,
            min_score=record.min_score / 100,
        )
        return {
            "saved_search": self.store.snapshot(record).__dict__,
            "results": [result.__dict__ for result in results],
        }

    async def export_json(self, repository_id: int | None = None) -> str:
        records = await self.store.list_all(repository_id)
        payload = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "count": len(records),
            "searches": [self.store.snapshot(record).__dict__ for record in records],
        }
        return json.dumps(payload, indent=2)

    async def import_results_preview(self, search_id: int) -> list[SearchResult]:
        payload = await self.run_saved(search_id)
        raw_results = payload["results"]
        return [
            SearchResult(
                entity_id=str(item["entity_id"]),
                score=float(item["score"]),
                file_path=str(item["file_path"]),
                start_line=int(item["start_line"]),
                end_line=int(item["end_line"]),
                entity_type=str(item["entity_type"]),
                snippet=str(item["snippet"]),
                repository_id=int(item["repository_id"]),
            )
            for item in raw_results
        ]
