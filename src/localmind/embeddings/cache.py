import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class CacheEntry:
    key: str
    vector: np.ndarray


class EmbeddingCache:
    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.cache_dir / "cache_index.json"
        self._index: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if not self.index_path.exists():
            return
        self._index = json.loads(self.index_path.read_text(encoding="utf-8"))

    def _persist(self) -> None:
        self.index_path.write_text(json.dumps(self._index, indent=2), encoding="utf-8")

    def key_for(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get(self, text: str) -> np.ndarray | None:
        key = self.key_for(text)
        filename = self._index.get(key)
        if filename is None:
            return None
        path = self.cache_dir / filename
        if not path.exists():
            return None
        return np.load(path)

    def set(self, text: str, vector: np.ndarray) -> None:
        key = self.key_for(text)
        filename = f"{key}.npy"
        path = self.cache_dir / filename
        np.save(path, vector)
        self._index[key] = filename
        self._persist()

    def bulk_get(self, texts: list[str]) -> tuple[list[str], list[np.ndarray | None]]:
        keys = [self.key_for(text) for text in texts]
        vectors = [self.get(text) for text in texts]
        return keys, vectors
