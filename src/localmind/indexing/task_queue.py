import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from localmind.core.logging import get_logger
from localmind.dashboard.progress import progress_hub
from localmind.indexing.models import IndexStatus
from localmind.indexing.store import IndexStore, IndexingService
from localmind.indexing.tasks import IndexTaskRecord, TaskStatus

logger = get_logger(__name__)


@dataclass(frozen=True)
class TaskSnapshot:
    id: int
    repository_id: int
    status: str
    attempts: int
    max_attempts: int
    last_error: str | None


class IndexTaskQueue:
    def __init__(self, session: AsyncSession, exclude_patterns: list[str]) -> None:
        self.session = session
        self.exclude_patterns = exclude_patterns
        self._workers: dict[int, asyncio.Task[None]] = {}

    async def enqueue(self, repository_id: int, incremental: bool = True, max_attempts: int = 3) -> IndexTaskRecord:
        task = IndexTaskRecord(
            repository_id=repository_id,
            incremental=1 if incremental else 0,
            max_attempts=max_attempts,
            status=TaskStatus.QUEUED.value,
        )
        self.session.add(task)
        await self.session.flush()
        return task

    async def get_task(self, task_id: int) -> IndexTaskRecord | None:
        result = await self.session.execute(select(IndexTaskRecord).where(IndexTaskRecord.id == task_id))
        return result.scalar_one_or_none()

    async def list_tasks(self, repository_id: int | None = None) -> list[IndexTaskRecord]:
        query = select(IndexTaskRecord).order_by(IndexTaskRecord.created_at.desc())
        if repository_id is not None:
            query = query.where(IndexTaskRecord.repository_id == repository_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def run_task(self, task_id: int) -> TaskSnapshot:
        task = await self.get_task(task_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found")

        store = IndexStore(self.session)
        service = IndexingService(store, self.exclude_patterns)
        repository = await store.get_repository_by_id(task.repository_id)
        if repository is None:
            task.status = TaskStatus.FAILED.value
            task.last_error = "Repository not found"
            task.finished_at = datetime.now(timezone.utc)
            await self.session.flush()
            return self._snapshot(task)

        task.attempts += 1
        task.status = TaskStatus.RUNNING.value
        task.started_at = datetime.now(timezone.utc)
        await self.session.flush()

        await progress_hub.emit_stage(
            task.repository_id,
            "queue",
            task.attempts,
            task.max_attempts,
            f"Running index task {task.id}",
        )

        try:
            stats = await service.index_repository(
                task.repository_id,
                incremental=bool(task.incremental),
            )
            task.status = TaskStatus.COMPLETED.value
            task.last_error = None
            task.finished_at = datetime.now(timezone.utc)
            await self.session.flush()
            await progress_hub.emit_stage(
                task.repository_id,
                "queue",
                stats["total"],
                stats["total"],
                f"Task {task.id} completed",
            )
            return self._snapshot(task)
        except Exception as exc:
            logger.exception("Index task %s failed", task.id)
            task.last_error = str(exc)
            if task.attempts < task.max_attempts:
                task.status = TaskStatus.RETRYING.value
                await self.session.flush()
                await progress_hub.emit_stage(
                    task.repository_id,
                    "queue",
                    task.attempts,
                    task.max_attempts,
                    f"Retry scheduled: {exc}",
                )
                return await self.run_task(task.id)
            task.status = TaskStatus.FAILED.value
            task.finished_at = datetime.now(timezone.utc)
            await store.set_status(repository, IndexStatus.FAILED)
            await self.session.flush()
            return self._snapshot(task)

    def _snapshot(self, task: IndexTaskRecord) -> TaskSnapshot:
        return TaskSnapshot(
            id=task.id,
            repository_id=task.repository_id,
            status=task.status,
            attempts=task.attempts,
            max_attempts=task.max_attempts,
            last_error=task.last_error,
        )
