from pathlib import Path

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from localmind.core.settings import Settings
from localmind.embeddings.cache import EmbeddingCache
from localmind.embeddings.encoder import EmbeddingRecord, SentenceTransformerEncoder
from localmind.embeddings.store import FaissVectorStore
from localmind.indexing.models import FileRecord, SymbolRecord


class EmbeddingPipeline:
    BATCH_SIZE = 32

    def __init__(self, settings: Settings, session: AsyncSession) -> None:
        self.settings = settings
        self.session = session
        self.cache = EmbeddingCache(settings.data_dir / "embedding_cache")
        self.encoder = SentenceTransformerEncoder(settings.embedding_model)
        self.vector_store = FaissVectorStore(
            settings.data_dir / "vectors" / "symbols.faiss",
            dimension=self.encoder.dimension,
        )

    async def embed_repository(self, repository_id: int) -> dict[str, int]:
        symbols = await self._load_symbols(repository_id)
        if not symbols:
            return {"embedded": 0, "cached": 0}

        texts = [self._symbol_text(symbol, file_record) for symbol, file_record in symbols]
        keys, cached_vectors = self.cache.bulk_get(texts)
        pending_texts: list[str] = []
        pending_indices: list[int] = []
        cached_count = 0

        for index, vector in enumerate(cached_vectors):
            if vector is None:
                pending_indices.append(index)
                pending_texts.append(texts[index])
            else:
                cached_count += 1

        generated_vectors: dict[int, np.ndarray] = {}
        if pending_texts:
            encoded = self.encoder.encode_batch(pending_texts, batch_size=self.BATCH_SIZE)
            for offset, source_index in enumerate(pending_indices):
                vector = encoded[offset]
                self.cache.set(texts[source_index], vector)
                generated_vectors[source_index] = vector

        embedded = 0
        for index, (symbol, file_record) in enumerate(symbols):
            vector = cached_vectors[index]
            if vector is None:
                vector = generated_vectors[index]
            record = EmbeddingRecord(
                entity_id=f"{repository_id}:{symbol.id}",
                entity_type=symbol.kind,
                repository_id=repository_id,
                file_path=file_record.relative_path,
                start_line=symbol.start_line,
                end_line=symbol.end_line,
                text=texts[index],
                vector=vector,
            )
            self.vector_store.upsert(record)
            embedded += 1

        self.vector_store.save()
        return {"embedded": embedded, "cached": cached_count}

    async def _load_symbols(self, repository_id: int) -> list[tuple[SymbolRecord, FileRecord]]:
        result = await self.session.execute(
            select(SymbolRecord, FileRecord)
            .join(FileRecord, SymbolRecord.file_id == FileRecord.id)
            .where(FileRecord.repository_id == repository_id)
            .order_by(FileRecord.relative_path, SymbolRecord.start_line)
        )
        return list(result.all())

    def _symbol_text(self, symbol: SymbolRecord, file_record: FileRecord) -> str:
        path = Path(file_record.absolute_path)
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        snippet = "\n".join(lines[symbol.start_line - 1 : symbol.end_line])
        docstring = symbol.docstring or ""
        return f"{file_record.relative_path}::{symbol.kind}::{symbol.name}\n{docstring}\n{snippet}"
