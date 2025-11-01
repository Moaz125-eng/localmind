from pathlib import Path

from pydantic import BaseModel, Field

from localmind.indexing.database import Database
from localmind.indexing.store import IndexStore, IndexingService
from localmind.indexing.task_queue import IndexTaskQueue


class RegisterRepositoryRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    root_path: str


class IndexRepositoryRequest(BaseModel):
    incremental: bool = True


class EnqueueIndexRequest(BaseModel):
    incremental: bool = True
    max_attempts: int = Field(default=3, ge=1, le=5)


class TaskResponse(BaseModel):
    id: int
    repository_id: int
    status: str
    attempts: int
    max_attempts: int
    last_error: str | None


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

    async def enqueue_index(self, repository_id: int, payload: EnqueueIndexRequest) -> TaskResponse:
        async with self.database.session() as session:
            store = IndexStore(session)
            repository = await store.get_repository_by_id(repository_id)
            if repository is None:
                raise ValueError(f"Repository {repository_id} not found")
            queue = IndexTaskQueue(session, self.exclude_patterns)
            task = await queue.enqueue(
                repository_id,
                incremental=payload.incremental,
                max_attempts=payload.max_attempts,
            )
            await session.commit()
            return TaskResponse(
                id=task.id,
                repository_id=task.repository_id,
                status=task.status,
                attempts=task.attempts,
                max_attempts=task.max_attempts,
                last_error=task.last_error,
            )

    async def run_index_task(self, task_id: int) -> TaskResponse:
        async with self.database.session() as session:
            queue = IndexTaskQueue(session, self.exclude_patterns)
            snapshot = await queue.run_task(task_id)
            await session.commit()
            return TaskResponse(
                id=snapshot.id,
                repository_id=snapshot.repository_id,
                status=snapshot.status,
                attempts=snapshot.attempts,
                max_attempts=snapshot.max_attempts,
                last_error=snapshot.last_error,
            )

    async def list_tasks(self, repository_id: int | None = None) -> list[TaskResponse]:
        async with self.database.session() as session:
            queue = IndexTaskQueue(session, self.exclude_patterns)
            tasks = await queue.list_tasks(repository_id)
            return [
                TaskResponse(
                    id=task.id,
                    repository_id=task.repository_id,
                    status=task.status,
                    attempts=task.attempts,
                    max_attempts=task.max_attempts,
                    last_error=task.last_error,
                )
                for task in tasks
            ]
