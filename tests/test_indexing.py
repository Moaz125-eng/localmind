import asyncio
from pathlib import Path

import pytest
from sqlalchemy import select

from localmind.core.settings import Settings
from localmind.indexing.database import Database
from localmind.indexing.models import FileRecord, RepositoryRecord, SymbolRecord
from localmind.indexing.scanner import RepositoryScanner
from localmind.indexing.store import IndexStore, IndexingService


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    return Settings(
        data_dir=data_dir,
        database_url=f"sqlite+aiosqlite:///{data_dir / 'test.db'}",
        index_exclude="venv,.git,__pycache__",
    )


@pytest.fixture
async def database(settings: Settings) -> Database:
    db = Database(settings)
    await db.init()
    return db


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "sample_repo"
    pkg = repo / "pkg"
    pkg.mkdir(parents=True)
    ignored = repo / "venv"
    ignored.mkdir(parents=True)
    (ignored / "ignored.py").write_text("ignored = True")
    (pkg / "module.py").write_text(
        "class Widget:\n"
        '    """Widget class."""\n'
        "    def spin(self):\n"
        "        return 1\n"
    )
    (pkg / "utils.py").write_text("def helper():\n    return helper()\n")
    return repo


def test_scanner_skips_excluded_directories(sample_repo: Path) -> None:
    scanner = RepositoryScanner(sample_repo, ["venv", ".git"])
    files = scanner.scan()
    paths = {item.relative_path for item in files}
    assert "pkg/module.py" in paths
    assert "pkg/utils.py" in paths
    assert not any("venv" in path for path in paths)


@pytest.mark.asyncio
async def test_incremental_indexing(database: Database, settings: Settings, sample_repo: Path) -> None:
    async with database.session() as session:
        store = IndexStore(session)
        service = IndexingService(store, settings.exclude_patterns)
        record = await service.register_repository("sample", sample_repo)
        first = await service.index_repository(record.id, incremental=False)
        second = await service.index_repository(record.id, incremental=True)
        await session.commit()

    assert first["indexed"] == 2
    assert second["skipped"] == 2
    assert second["indexed"] == 0


@pytest.mark.asyncio
async def test_symbol_extraction(database: Database, settings: Settings, sample_repo: Path) -> None:
    async with database.session() as session:
        store = IndexStore(session)
        service = IndexingService(store, settings.exclude_patterns)
        record = await service.register_repository("sample", sample_repo)
        await service.index_repository(record.id, incremental=False)
        result = await session.execute(select(SymbolRecord))
        symbols = list(result.scalars().all())
        await session.commit()

    names = {symbol.name for symbol in symbols}
    assert "Widget" in names
    assert "spin" in names
    assert "helper" in names


@pytest.mark.asyncio
async def test_stale_file_removal(database: Database, settings: Settings, sample_repo: Path) -> None:
    utils_path = sample_repo / "pkg" / "utils.py"
    async with database.session() as session:
        store = IndexStore(session)
        service = IndexingService(store, settings.exclude_patterns)
        record = await service.register_repository("sample", sample_repo)
        await service.index_repository(record.id, incremental=False)
        utils_path.unlink()
        stats = await service.index_repository(record.id, incremental=True)
        files = await store.get_files(record.id)
        await session.commit()

    assert stats["removed"] == 1
    assert len(files) == 1
