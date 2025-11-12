from pathlib import Path

import pytest

from localmind.core.settings import Settings
from localmind.indexing.database import Database
from localmind.indexing.snapshot import SnapshotExporter
from localmind.indexing.store import IndexStore, IndexingService


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    return Settings(
        data_dir=data_dir,
        database_url=f"sqlite+aiosqlite:///{data_dir / 'snap.db'}",
    )


@pytest.fixture
async def database(settings: Settings) -> Database:
    db = Database(settings)
    await db.init()
    return db


@pytest.mark.asyncio
async def test_snapshot_exporter(database: Database, settings: Settings, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "service.py").write_text("class Service:\n    def run(self):\n        return True\n")
    async with database.session() as session:
        store = IndexStore(session)
        service = IndexingService(store, settings.exclude_patterns)
        record = await service.register_repository("snap", repo)
        await service.index_repository(record.id, incremental=False)
        exporter = SnapshotExporter(session)
        snapshot = await exporter.export(record.id)
        payload = exporter.to_json(snapshot)
        await session.commit()

    assert snapshot.files
    assert snapshot.symbols
    assert "Service" in payload
