from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from localmind.core.logging import get_logger
from localmind.indexing.models import FileRecord, IndexStatus, RepositoryRecord, SymbolRecord
from localmind.indexing.scanner import RepositoryScanner, ScannedFile
from localmind.indexing.symbols import PythonSymbolExtractor

logger = get_logger(__name__)


class IndexStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_repository_by_name(self, name: str) -> RepositoryRecord | None:
        result = await self.session.execute(
            select(RepositoryRecord).where(RepositoryRecord.name == name)
        )
        return result.scalar_one_or_none()

    async def get_repository_by_id(self, repository_id: int) -> RepositoryRecord | None:
        result = await self.session.execute(
            select(RepositoryRecord).where(RepositoryRecord.id == repository_id)
        )
        return result.scalar_one_or_none()

    async def list_repositories(self) -> list[RepositoryRecord]:
        result = await self.session.execute(select(RepositoryRecord).order_by(RepositoryRecord.name))
        return list(result.scalars().all())

    async def create_repository(self, name: str, root_path: Path) -> RepositoryRecord:
        record = RepositoryRecord(name=name, root_path=str(root_path.resolve()))
        self.session.add(record)
        await self.session.flush()
        return record

    async def set_status(self, repository: RepositoryRecord, status: IndexStatus) -> None:
        repository.status = status.value
        await self.session.flush()

    async def get_files(self, repository_id: int) -> list[FileRecord]:
        result = await self.session.execute(
            select(FileRecord).where(FileRecord.repository_id == repository_id)
        )
        return list(result.scalars().all())

    async def upsert_file(self, repository: RepositoryRecord, scanned: ScannedFile) -> FileRecord:
        result = await self.session.execute(
            select(FileRecord).where(
                FileRecord.repository_id == repository.id,
                FileRecord.relative_path == scanned.relative_path,
            )
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            existing = FileRecord(
                repository_id=repository.id,
                relative_path=scanned.relative_path,
                absolute_path=str(scanned.absolute_path),
                extension=scanned.extension,
                size_bytes=scanned.size_bytes,
                content_hash=scanned.content_hash,
                modified_at=scanned.modified_at,
            )
            self.session.add(existing)
        else:
            existing.absolute_path = str(scanned.absolute_path)
            existing.extension = scanned.extension
            existing.size_bytes = scanned.size_bytes
            existing.content_hash = scanned.content_hash
            existing.modified_at = scanned.modified_at
            existing.indexed_at = datetime.now(timezone.utc)
        await self.session.flush()
        return existing

    async def replace_symbols(self, file_record: FileRecord, symbols: list[SymbolRecord]) -> None:
        await self.session.execute(delete(SymbolRecord).where(SymbolRecord.file_id == file_record.id))
        self.session.add_all(symbols)
        await self.session.flush()

    async def remove_stale_files(
        self, repository: RepositoryRecord, active_paths: set[str]
    ) -> int:
        files = await self.get_files(repository.id)
        removed = 0
        for file_record in files:
            if file_record.relative_path not in active_paths:
                await self.session.execute(
                    delete(SymbolRecord).where(SymbolRecord.file_id == file_record.id)
                )
                await self.session.delete(file_record)
                removed += 1
        await self.session.flush()
        return removed

    async def finalize(self, repository: RepositoryRecord, file_count: int) -> None:
        repository.file_count = file_count
        repository.last_indexed_at = datetime.now(timezone.utc)
        repository.status = IndexStatus.COMPLETED.value
        await self.session.flush()


class IndexingService:
    def __init__(self, store: IndexStore, exclude_patterns: list[str]) -> None:
        self.store = store
        self.exclude_patterns = exclude_patterns
        self.extractor = PythonSymbolExtractor()

    async def register_repository(self, name: str, root_path: Path) -> RepositoryRecord:
        existing = await self.store.get_repository_by_name(name)
        if existing is not None:
            existing.root_path = str(root_path.resolve())
            return existing
        return await self.store.create_repository(name, root_path)

    async def index_repository(self, repository_id: int, incremental: bool = True) -> dict[str, int]:
        repository = await self.store.get_repository_by_id(repository_id)
        if repository is None:
            raise ValueError(f"Repository {repository_id} not found")

        await self.store.set_status(repository, IndexStatus.RUNNING)
        root_path = Path(repository.root_path)
        scanner = RepositoryScanner(root_path, self.exclude_patterns)
        scanned_files = scanner.scan()
        active_paths = {item.relative_path for item in scanned_files}
        indexed = 0
        skipped = 0

        existing_files = {file.relative_path: file for file in await self.store.get_files(repository.id)}

        for scanned in scanned_files:
            previous = existing_files.get(scanned.relative_path)
            if incremental and previous is not None and previous.content_hash == scanned.content_hash:
                skipped += 1
                continue

            file_record = await self.store.upsert_file(repository, scanned)
            source = scanned.absolute_path.read_text(encoding="utf-8", errors="replace")
            symbols = self.extractor.build_records(file_record, source)
            await self.store.replace_symbols(file_record, symbols)
            indexed += 1

        removed = await self.store.remove_stale_files(repository, active_paths)
        await self.store.finalize(repository, len(scanned_files))
        logger.info(
            "Indexed repository %s indexed=%s skipped=%s removed=%s",
            repository.name,
            indexed,
            skipped,
            removed,
        )
        return {"indexed": indexed, "skipped": skipped, "removed": removed, "total": len(scanned_files)}
