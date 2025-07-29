from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from localmind.core.settings import Settings
from localmind.embeddings.cache import EmbeddingCache
from localmind.embeddings.encoder import EmbeddingRecord, SentenceTransformerEncoder
from localmind.embeddings.store import FaissVectorStore


def test_embedding_cache_roundtrip(tmp_path: Path) -> None:
    cache = EmbeddingCache(tmp_path / "cache")
    vector = np.array([0.1, 0.2, 0.3], dtype=np.float32)
    cache.set("hello world", vector)
    loaded = cache.get("hello world")
    assert loaded is not None
    assert np.allclose(loaded, vector)


def test_faiss_store_upsert_and_search(tmp_path: Path) -> None:
    store = FaissVectorStore(tmp_path / "index.faiss", dimension=4)
    first = EmbeddingRecord(
        entity_id="1:1",
        entity_type="function",
        repository_id=1,
        file_path="a.py",
        start_line=1,
        end_line=3,
        text="alpha",
        vector=np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32),
    )
    second = EmbeddingRecord(
        entity_id="1:2",
        entity_type="function",
        repository_id=1,
        file_path="b.py",
        start_line=1,
        end_line=3,
        text="beta",
        vector=np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32),
    )
    store.upsert(first)
    store.upsert(second)
    store.save()

    reloaded = FaissVectorStore(tmp_path / "index.faiss", dimension=4)
    hits = reloaded.search(np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32), limit=1)
    assert hits
    assert hits[0].entity_id == "1:1"


def test_encoder_batch_dimension(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_model = MagicMock()
    fake_model.get_sentence_embedding_dimension.return_value = 3
    fake_model.encode.return_value = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]], dtype=np.float32)

    def loader(_model_name: str):
        return fake_model

    monkeypatch.setattr(
        "localmind.embeddings.encoder.SentenceTransformerEncoder._load_model",
        lambda self: fake_model,
    )
    encoder = SentenceTransformerEncoder("fake-model")
    vectors = encoder.encode_batch(["one", "two"])
    assert vectors.shape == (2, 3)
