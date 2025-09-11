import argparse
import asyncio
from pathlib import Path

from localmind.core.settings import Settings
from localmind.dashboard.progress import progress_hub
from localmind.embeddings.pipeline import EmbeddingPipeline
from localmind.indexing.database import Database
from localmind.indexing.store import IndexStore, IndexingService


async def run_index(name: str, root_path: Path, incremental: bool, embed: bool) -> None:
    settings = Settings()
    settings.ensure_data_dir()
    database = Database(settings)
    await database.init()

    async with database.session() as session:
        store = IndexStore(session)
        service = IndexingService(store, settings.exclude_patterns)
        repository = await service.register_repository(name, root_path)
        await session.commit()
        repository_id = repository.id

    await progress_hub.emit_stage(repository_id, "scan", 0, 1, "Starting repository scan")

    async with database.session() as session:
        store = IndexStore(session)
        service = IndexingService(store, settings.exclude_patterns)
        stats = await service.index_repository(repository_id, incremental=incremental)
        await session.commit()

    await progress_hub.emit_stage(
        repository_id,
        "index",
        stats["total"],
        stats["total"],
        f"Indexed {stats['indexed']} files",
    )

    if embed:
        await progress_hub.emit_stage(repository_id, "embed", 0, 1, "Generating embeddings")
        async with database.session() as session:
            pipeline = EmbeddingPipeline(settings, session)
            embed_stats = await pipeline.embed_repository(repository_id)
            await session.commit()
        await progress_hub.emit_stage(
            repository_id,
            "embed",
            embed_stats["embedded"],
            embed_stats["embedded"],
            "Embedding complete",
        )

    print(
        f"Repository '{name}' indexed: "
        f"{stats['indexed']} updated, {stats['skipped']} skipped, {stats['removed']} removed"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Index a repository with LocalMind")
    parser.add_argument("name")
    parser.add_argument("path")
    parser.add_argument("--full", action="store_true", help="Disable incremental indexing")
    parser.add_argument("--embed", action="store_true", help="Generate embeddings after indexing")
    args = parser.parse_args()
    asyncio.run(run_index(args.name, Path(args.path), incremental=not args.full, embed=args.embed))


if __name__ == "__main__":
    main()
