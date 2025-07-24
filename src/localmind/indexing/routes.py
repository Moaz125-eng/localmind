from pathlib import Path

from pydantic import BaseModel, Field

from localmind.indexing.database import Database
from localmind.indexing.store import IndexStore, IndexingService


class RegisterRepositoryRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    root_path: str


class IndexRepositoryRequest(BaseModel):
    incremental: bool = True


class RepositoryResponse(BaseModel):
    id: int
    name: str
    root_path: str
    status: str
    file_count: int
    last_indexed_at: str | None


class IndexingRouterFactory:
    def __init__(self, database: Database, exclude_patterns: list[str]) -> None:
        self.database = database
        self.exclude_patterns = exclude_patterns

    def _to_response(self, record) -> RepositoryResponse:
        return RepositoryResponse(
            id=record.id,
            name=record.name,
            root_path=record.root_path,
            status=record.status,
            file_count=record.file_count,
            last_indexed_at=record.last_indexed_at.isoformat() if record.last_indexed_at else None,
        )

    async def list_repositories(self) -> list[RepositoryResponse]:
        async with self.database.session() as session:
            store = IndexStore(session)
            records = await store.list_repositories()
            return [self._to_response(record) for record in records]

    async def register_repository(self, payload: RegisterRepositoryRequest) -> RepositoryResponse:
        async with self.database.session() as session:
            store = IndexStore(session)
            service = IndexingService(store, self.exclude_patterns)
            record = await service.register_repository(payload.name, Path(payload.root_path))
            await session.commit()
            return self._to_response(record)

    async def index_repository(
        self, repository_id: int, payload: IndexRepositoryRequest
    ) -> dict[str, int | RepositoryResponse]:
        async with self.database.session() as session:
            store = IndexStore(session)
            service = IndexingService(store, self.exclude_patterns)
            stats = await service.index_repository(repository_id, incremental=payload.incremental)
            record = await store.get_repository_by_id(repository_id)
            await session.commit()
            response = self._to_response(record) if record else None
            return {"stats": stats, "repository": response.model_dump() if response else None}
