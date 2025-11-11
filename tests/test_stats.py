from pathlib import Path

import pytest

from localmind.core.settings import Settings
from localmind.indexing.database import Database
from localmind.indexing.stats import RepositoryStatsService
from localmind.indexing.store import IndexStore, IndexingService


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    return Settings(
        data_dir=data_dir,
        database_url=f"sqlite+aiosqlite:///{data_dir / 'stats.db'}",
    )


@pytest.fixture
async def database(settings: Settings) -> Database:
    db = Database(settings)
    await db.init()
    return db


@pytest.mark.asyncio
async def test_repository_stats_summary(database: Database, settings: Settings, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("def main():\n    return 1\n")
    async with database.session() as session:
        store = IndexStore(session)
        service = IndexingService(store, settings.exclude_patterns)
        record = await service.register_repository("stats-demo", repo)
        await service.index_repository(record.id, incremental=False)
        stats_service = RepositoryStatsService(session)
        summary = await stats_service.summary(record.id)
        global_summary = await stats_service.global_summary()
        await session.commit()

    assert summary["files"] == 1
    assert summary["symbols"] >= 1
    assert global_summary["repositories"] == 1
