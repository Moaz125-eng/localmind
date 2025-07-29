from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from localmind.core.settings import Settings
from localmind.embeddings.encoder import EmbeddingRecord
from localmind.embeddings.store import FaissVectorStore
from localmind.search.engine import SemanticSearchEngine


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path / "data")


def test_semantic_search_filters_by_repository(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    store = FaissVectorStore(settings.data_dir / "vectors" / "symbols.faiss", dimension=3)
    store.upsert(
        EmbeddingRecord(
            entity_id="1:1",
            entity_type="function",
            repository_id=1,
            file_path="auth.py",
            start_line=1,
            end_line=5,
            text="auth.py::function::verify_jwt\nverify jwt token",
            vector=np.array([1.0, 0.1, 0.0], dtype=np.float32),
        )
    )
    store.upsert(
        EmbeddingRecord(
            entity_id="2:1",
            entity_type="function",
            repository_id=2,
            file_path="db.py",
            start_line=10,
            end_line=20,
            text="db.py::function::run_transaction\nhandle db transaction",
            vector=np.array([0.9, 0.2, 0.0], dtype=np.float32),
        )
    )
    store.save()

    fake_encoder = MagicMock()
    fake_encoder.dimension = 3
    fake_encoder.encode_batch.return_value = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)

    engine = SemanticSearchEngine(settings)
    engine.encoder = fake_encoder
    engine.vector_store = FaissVectorStore(settings.data_dir / "vectors" / "symbols.faiss", dimension=3)

    all_results = engine.search("jwt authentication", limit=5, min_score=0.1)
    repo_results = engine.search("jwt authentication", repository_id=1, limit=5, min_score=0.1)

    assert all_results
    assert repo_results
    assert all(item.repository_id == 1 for item in repo_results)


def test_search_result_contains_line_numbers(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    store = FaissVectorStore(settings.data_dir / "vectors" / "symbols.faiss", dimension=2)
    store.upsert(
        EmbeddingRecord(
            entity_id="1:9",
            entity_type="function",
            repository_id=1,
            file_path="ws.py",
            start_line=12,
            end_line=28,
            text="ws.py::function::connect_socket\nwebsocket connect handler",
            vector=np.array([1.0, 0.0], dtype=np.float32),
        )
    )
    store.save()

    fake_encoder = MagicMock()
    fake_encoder.dimension = 2
    fake_encoder.encode_batch.return_value = np.array([[1.0, 0.0]], dtype=np.float32)

    engine = SemanticSearchEngine(settings)
    engine.encoder = fake_encoder
    engine.vector_store = FaissVectorStore(settings.data_dir / "vectors" / "symbols.faiss", dimension=2)
    results = engine.search("websocket logic", limit=1, min_score=0.1)

    assert results[0].file_path == "ws.py"
    assert results[0].start_line == 12
    assert results[0].end_line == 28
