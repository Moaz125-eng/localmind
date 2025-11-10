from pathlib import Path

import pytest

from localmind.core.settings import Settings
from localmind.indexing.database import Database
from localmind.indexing.store import IndexStore, IndexingService
from localmind.indexing.task_queue import IndexTaskQueue
from localmind.indexing.tasks import TaskStatus


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    return Settings(
        data_dir=data_dir,
        database_url=f"sqlite+aiosqlite:///{data_dir / 'tasks.db'}",
    )


@pytest.fixture
async def database(settings: Settings) -> Database:
    db = Database(settings)
    await db.init()
    return db


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text("def run():\n    return 1\n")
    return repo


@pytest.mark.asyncio
async def test_enqueue_and_run_task(database: Database, settings: Settings, sample_repo: Path) -> None:
    async with database.session() as session:
        store = IndexStore(session)
        service = IndexingService(store, settings.exclude_patterns)
        record = await service.register_repository("demo", sample_repo)
        await session.commit()
        repo_id = record.id

    async with database.session() as session:
        queue = IndexTaskQueue(session, settings.exclude_patterns)
        task = await queue.enqueue(repo_id, incremental=False)
        await session.commit()
        task_id = task.id

    async with database.session() as session:
        queue = IndexTaskQueue(session, settings.exclude_patterns)
        snapshot = await queue.run_task(task_id)
        await session.commit()

    assert snapshot.status == TaskStatus.COMPLETED.value
    assert snapshot.attempts == 1


@pytest.mark.asyncio
async def test_task_retries_on_failure(database: Database, settings: Settings, tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    async with database.session() as session:
        store = IndexStore(session)
        service = IndexingService(store, settings.exclude_patterns)
        record = await service.register_repository("broken", missing)
        await session.commit()
        repo_id = record.id

    async with database.session() as session:
        queue = IndexTaskQueue(session, settings.exclude_patterns)
        task = await queue.enqueue(repo_id, max_attempts=2)
        await session.commit()
        task_id = task.id

    async with database.session() as session:
        queue = IndexTaskQueue(session, settings.exclude_patterns)
        snapshot = await queue.run_task(task_id)
        await session.commit()

    assert snapshot.status == TaskStatus.FAILED.value
    assert snapshot.attempts == 2
