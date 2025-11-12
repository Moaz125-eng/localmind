import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from localmind.core.settings import Settings
from localmind.indexing.database import Database
from localmind.indexing.models import FileRecord, RepositoryRecord, SymbolRecord
from localmind.indexing.stats import RepositoryStatsService
from localmind.indexing.store import IndexStore


@dataclass(frozen=True)
class SnapshotFile:
    relative_path: str
    extension: str
    size_bytes: int
    content_hash: str


@dataclass(frozen=True)
class SnapshotSymbol:
    relative_path: str
    name: str
    kind: str
    start_line: int
    end_line: int


@dataclass
class RepositorySnapshot:
    exported_at: str
    repository: dict[str, object]
    stats: dict[str, int | str | None]
    files: list[SnapshotFile]
    symbols: list[SnapshotSymbol]


class SnapshotExporter:
    def __init__(self, session) -> None:
        self.session = session

    async def export(self, repository_id: int) -> RepositorySnapshot:
        repository = await self.session.get(RepositoryRecord, repository_id)
        if repository is None:
            raise ValueError(f"Repository {repository_id} not found")

        stats = await RepositoryStatsService(self.session).summary(repository_id)
        files_result = await self.session.execute(
            select(FileRecord).where(FileRecord.repository_id == repository_id)
        )
        files = list(files_result.scalars().all())
        symbols_result = await self.session.execute(
            select(SymbolRecord, FileRecord)
            .join(FileRecord, SymbolRecord.file_id == FileRecord.id)
            .where(FileRecord.repository_id == repository_id)
        )
        symbol_rows = list(symbols_result.all())

        return RepositorySnapshot(
            exported_at=datetime.now(timezone.utc).isoformat(),
            repository={
                "id": repository.id,
                "name": repository.name,
                "root_path": repository.root_path,
                "status": repository.status,
            },
            stats=stats,
            files=[
                SnapshotFile(
                    relative_path=file.relative_path,
                    extension=file.extension,
                    size_bytes=file.size_bytes,
                    content_hash=file.content_hash,
                )
                for file in files
            ],
            symbols=[
                SnapshotSymbol(
                    relative_path=file.relative_path,
                    name=symbol.name,
                    kind=symbol.kind,
                    start_line=symbol.start_line,
                    end_line=symbol.end_line,
                )
                for symbol, file in symbol_rows
            ],
        )

    def to_json(self, snapshot: RepositorySnapshot) -> str:
        payload = {
            "exported_at": snapshot.exported_at,
            "repository": snapshot.repository,
            "stats": snapshot.stats,
            "files": [asdict(item) for item in snapshot.files],
            "symbols": [asdict(item) for item in snapshot.symbols],
        }
        return json.dumps(payload, indent=2)


async def export_repository_snapshot(settings: Settings, repository_id: int, output_path: Path) -> Path:
    settings.ensure_data_dir()
    database = Database(settings)
    await database.init()
    async with database.session() as session:
        exporter = SnapshotExporter(session)
        snapshot = await exporter.export(repository_id)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(exporter.to_json(snapshot), encoding="utf-8")
    return output_path


async def print_diagnostics(settings: Settings) -> None:
    database = Database(settings)
    await database.init()
    async with database.session() as session:
        store = IndexStore(session)
        repositories = await store.list_repositories()
        stats_service = RepositoryStatsService(session)
        global_stats = await stats_service.global_summary()
    print(json.dumps({"global": global_stats, "repositories": len(repositories)}, indent=2))
