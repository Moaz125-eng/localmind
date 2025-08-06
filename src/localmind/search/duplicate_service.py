import json
from pathlib import Path

import numpy as np

from localmind.core.settings import Settings
from localmind.embeddings.store import FaissVectorStore
from localmind.search.duplicates import DuplicatePair


class DuplicateDetector:
    def __init__(self, settings: Settings, threshold: float = 0.88) -> None:
        self.settings = settings
        self.threshold = threshold
        self.vector_store = FaissVectorStore(
            settings.data_dir / "vectors" / "symbols.faiss",
            dimension=self._load_dimension(settings),
        )

    def _load_dimension(self, settings: Settings) -> int:
        metadata_path = settings.data_dir / "vectors" / "symbols.meta.json"
        if metadata_path.exists():
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            records = payload.get("records", [])
            if records:
                return len(self.vector_store.index.reconstruct(0)) if False else 384
        return 384

    def find_duplicates(self, repository_id: int | None = None, limit: int = 50) -> list[DuplicatePair]:
        records = self.vector_store.metadata
        filtered = [
            (index, record)
            for index, record in enumerate(records)
            if repository_id is None or record.get("repository_id") == repository_id
        ]
        pairs: list[DuplicatePair] = []
        for left_index, left_record in filtered:
            vector = self.vector_store.index.reconstruct(left_index)
            hits = self.vector_store.search(vector, limit=5)
            for hit in hits:
                if hit.entity_id == left_record["entity_id"]:
                    continue
                if hit.score < self.threshold:
                    continue
                right = hit.metadata
                pairs.append(
                    DuplicatePair(
                        left_entity_id=str(left_record["entity_id"]),
                        right_entity_id=str(right["entity_id"]),
                        similarity=hit.score,
                        left_file=str(left_record["file_path"]),
                        right_file=str(right["file_path"]),
                        left_start_line=int(left_record["start_line"]),
                        right_start_line=int(right["start_line"]),
                        left_snippet=str(left_record.get("text", ""))[:240],
                        right_snippet=str(right.get("text", ""))[:240],
                    )
                )
                if len(pairs) >= limit:
                    return pairs
        return pairs
