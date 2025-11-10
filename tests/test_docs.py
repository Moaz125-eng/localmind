from pathlib import Path

import pytest

from localmind.core.settings import Settings
from localmind.indexing.database import Database
from localmind.indexing.doc_service import DocumentationIndexService
from localmind.indexing.docs import DocumentationIndexer, MarkdownChunkParser
from localmind.indexing.store import IndexStore, IndexingService


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    return Settings(
        data_dir=data_dir,
        database_url=f"sqlite+aiosqlite:///{data_dir / 'docs.db'}",
    )


@pytest.fixture
async def database(settings: Settings) -> Database:
    db = Database(settings)
    await db.init()
    return db


def test_markdown_parser_splits_headings_and_code(tmp_path: Path) -> None:
    doc = tmp_path / "guide.md"
    doc.write_text(
        "# Setup\n\n"
        "Install deps first.\n\n"
        "```bash\n"
        "pip install -e .\n"
        "```\n\n"
        "## Run\n\n"
        "Start the server.\n"
    )
    parser = MarkdownChunkParser()
    chunks = parser.parse_file(tmp_path, doc)
    kinds = {chunk.kind for chunk in chunks}
    assert "heading" in kinds
    assert "paragraph" in kinds
    assert "code" in kinds


def test_documentation_indexer_scan(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "readme.md").write_text("# LocalMind\n\nLocal indexing engine.\n")
    indexer = DocumentationIndexer()
    chunks = indexer.scan(tmp_path, [".git"])
    assert chunks


@pytest.mark.asyncio
async def test_documentation_index_service(database: Database, settings: Settings, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    docs = repo / "docs"
    docs.mkdir(parents=True)
    (docs / "architecture.md").write_text("# Architecture\n\nModules are split by layer.\n")
    async with database.session() as session:
        store = IndexStore(session)
        service = IndexingService(store, settings.exclude_patterns)
        record = await service.register_repository("docs-repo", repo)
        await session.commit()
        repo_id = record.id

    async with database.session() as session:
        doc_service = DocumentationIndexService(session, settings.exclude_patterns)
        stats = await doc_service.index_docs(repo_id)
        listed = await doc_service.list_chunks(repo_id)
        await session.commit()

    assert stats["chunks"] >= 2
    assert listed
