import json
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np

from localmind.embeddings.encoder import EmbeddingRecord


@dataclass
class VectorSearchHit:
    entity_id: str
    score: float
    metadata: dict[str, object]


class FaissVectorStore:
    def __init__(self, index_path: Path, dimension: int) -> None:
        self.index_path = index_path
        self.metadata_path = index_path.with_suffix(".meta.json")
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.metadata: list[dict[str, object]] = []
        self.entity_index: dict[str, int] = {}
        self._load()

    def _load(self) -> None:
        if not self.index_path.exists():
            return
        self.index = faiss.read_index(str(self.index_path))
        payload = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        self.metadata = payload["records"]
        self.entity_index = payload["entity_index"]

    def save(self) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.index_path))
        payload = {"records": self.metadata, "entity_index": self.entity_index}
        self.metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def upsert(self, record: EmbeddingRecord) -> None:
        vector = record.vector.astype(np.float32)
        faiss.normalize_L2(vector.reshape(1, -1))
        if record.entity_id in self.entity_index:
            position = self.entity_index[record.entity_id]
            self.metadata[position] = self._metadata(record)
            self.index.remove_ids(np.array([position], dtype=np.int64))
            self.index.add_with_ids(vector.reshape(1, -1), np.array([position], dtype=np.int64))
            return

        position = len(self.metadata)
        self.metadata.append(self._metadata(record))
        self.entity_index[record.entity_id] = position
        self.index.add_with_ids(vector.reshape(1, -1), np.array([position], dtype=np.int64))

    def search(self, query_vector: np.ndarray, limit: int = 10) -> list[VectorSearchHit]:
        if self.index.ntotal == 0:
            return []
        vector = query_vector.astype(np.float32).reshape(1, -1)
        faiss.normalize_L2(vector)
        scores, ids = self.index.search(vector, min(limit, self.index.ntotal))
        hits: list[VectorSearchHit] = []
        for score, position in zip(scores[0], ids[0], strict=False):
            if position < 0:
                continue
            metadata = self.metadata[position]
            hits.append(
                VectorSearchHit(
                    entity_id=str(metadata["entity_id"]),
                    score=float(score),
                    metadata=metadata,
                )
            )
        return hits

    def count(self) -> int:
        return self.index.ntotal

    def _metadata(self, record: EmbeddingRecord) -> dict[str, object]:
        return {
            "entity_id": record.entity_id,
            "entity_type": record.entity_type,
            "repository_id": record.repository_id,
            "file_path": record.file_path,
            "start_line": record.start_line,
            "end_line": record.end_line,
            "text": record.text,
        }
