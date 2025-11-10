from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from localmind.indexing.doc_models import DocChunkRecord
from localmind.indexing.docs import DocumentationIndexer
from localmind.indexing.store import IndexStore


class DocumentationIndexService:
    def __init__(self, session: AsyncSession, exclude_patterns: list[str]) -> None:
        self.session = session
        self.exclude_patterns = exclude_patterns
        self.indexer = DocumentationIndexer()

    async def index_docs(self, repository_id: int) -> dict[str, int]:
        store = IndexStore(self.session)
        repository = await store.get_repository_by_id(repository_id)
        if repository is None:
            raise ValueError(f"Repository {repository_id} not found")

        root_path = Path(repository.root_path)
        chunks = self.indexer.scan(root_path, self.exclude_patterns)
        await self.session.execute(
            delete(DocChunkRecord).where(DocChunkRecord.repository_id == repository_id)
        )
        records = self.indexer.to_records(repository_id, chunks)
        self.session.add_all(records)
        await self.session.flush()
        return {
            "files": len({chunk.relative_path for chunk in chunks}),
            "chunks": len(chunks),
        }

    async def list_chunks(self, repository_id: int, limit: int = 100) -> list[DocChunkRecord]:
        result = await self.session.execute(
            select(DocChunkRecord)
            .where(DocChunkRecord.repository_id == repository_id)
            .order_by(DocChunkRecord.relative_path, DocChunkRecord.start_line)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_chunks(self, repository_id: int, query: str, limit: int = 20) -> list[DocChunkRecord]:
        lowered = query.lower()
        result = await self.session.execute(
            select(DocChunkRecord).where(DocChunkRecord.repository_id == repository_id)
        )
        matches = [
            record
            for record in result.scalars().all()
            if lowered in record.content.lower() or lowered in record.title.lower()
        ]
        return matches[:limit]
