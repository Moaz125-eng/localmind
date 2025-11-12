from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from localmind.indexing.doc_models import DocChunkRecord
from localmind.indexing.models import FileRecord, RepositoryRecord, SymbolRecord
from localmind.indexing.tasks import IndexTaskRecord, TaskStatus
from localmind.search.saved_models import SavedSearchRecord


class RepositoryStatsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def summary(self, repository_id: int) -> dict[str, int | str | None]:
        repository = await self.session.get(RepositoryRecord, repository_id)
        if repository is None:
            raise ValueError(f"Repository {repository_id} not found")

        file_count = await self._count(FileRecord, FileRecord.repository_id == repository_id)
        symbol_count = await self._count(
            SymbolRecord,
            SymbolRecord.file_id.in_(select(FileRecord.id).where(FileRecord.repository_id == repository_id)),
        )
        doc_count = await self._count(DocChunkRecord, DocChunkRecord.repository_id == repository_id)
        saved_count = await self._count(SavedSearchRecord, SavedSearchRecord.repository_id == repository_id)
        failed_tasks = await self._count(
            IndexTaskRecord,
            (IndexTaskRecord.repository_id == repository_id)
            & (IndexTaskRecord.status == TaskStatus.FAILED.value),
        )

        return {
            "repository_id": repository_id,
            "name": repository.name,
            "status": repository.status,
            "files": file_count,
            "symbols": symbol_count,
            "doc_chunks": doc_count,
            "saved_searches": saved_count,
            "failed_tasks": failed_tasks,
            "last_indexed_at": repository.last_indexed_at.isoformat() if repository.last_indexed_at else None,
        }

    async def global_summary(self) -> dict[str, int]:
        repositories = await self._count(RepositoryRecord)
        files = await self._count(FileRecord)
        symbols = await self._count(SymbolRecord)
        docs = await self._count(DocChunkRecord)
        return {
            "repositories": repositories,
            "files": files,
            "symbols": symbols,
            "doc_chunks": docs,
        }

    async def _count(self, model, condition=None) -> int:
        stmt = select(func.count()).select_from(model)
        if condition is not None:
            stmt = stmt.where(condition)
        result = await self.session.execute(stmt)
        return int(result.scalar_one())
