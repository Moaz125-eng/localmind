from unittest.mock import MagicMock

import pytest

from localmind.core.settings import Settings
from localmind.indexing.database import Database
from localmind.search.models import SearchResult
from localmind.search.saved import SavedSearchService


@pytest.fixture
def settings(tmp_path):
    data_dir = tmp_path / "data"
    return Settings(
        data_dir=data_dir,
        database_url=f"sqlite+aiosqlite:///{data_dir / 'saved.db'}",
    )


@pytest.fixture
async def database(settings):
    db = Database(settings)
    await db.init()
    return db


@pytest.mark.asyncio
async def test_save_and_export_searches(database, settings) -> None:
    engine = MagicMock()
    engine.search.return_value = [
        SearchResult(
            entity_id="1:1",
            score=0.9,
            file_path="auth.py",
            start_line=1,
            end_line=5,
            entity_type="function",
            snippet="verify token",
            repository_id=1,
        )
    ]
    async with database.session() as session:
        service = SavedSearchService(session, engine)
        saved = await service.save("jwt lookup", "jwt auth", 1, 0.2, 5)
        exported = await service.export_json(1)
        ran = await service.run_saved(saved.id)
        await session.commit()

    assert "jwt lookup" in exported
    assert ran["results"]


@pytest.mark.asyncio
async def test_delete_saved_search(database, settings) -> None:
    engine = MagicMock()
    async with database.session() as session:
        service = SavedSearchService(session, engine)
        saved = await service.save("temp", "query", None, 0.1, 5)
        deleted = await service.store.delete(saved.id)
        await session.commit()

    assert deleted is True
