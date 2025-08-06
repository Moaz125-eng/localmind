from pathlib import Path

import numpy as np
import pytest

from localmind.core.settings import Settings
from localmind.embeddings.encoder import EmbeddingRecord
from localmind.embeddings.store import FaissVectorStore
from localmind.parsers.analyzer import RepositoryAnalyzer
from localmind.rag.refactor import RefactorAdvisor
from localmind.rag.ollama import OllamaClient
from localmind.search.duplicate_service import DuplicateDetector
from tests.test_parsers import build_repo


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path / "data")


def seed_similar_vectors(settings: Settings) -> None:
    store = FaissVectorStore(settings.data_dir / "vectors" / "symbols.faiss", dimension=3)
    base = np.array([1.0, 0.1, 0.0], dtype=np.float32)
    near = np.array([0.99, 0.11, 0.0], dtype=np.float32)
    far = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    store.upsert(
        EmbeddingRecord(
            entity_id="1:1",
            entity_type="function",
            repository_id=1,
            file_path="a.py",
            start_line=1,
            end_line=5,
            text="def normalize_user(input): ...",
            vector=base,
        )
    )
    store.upsert(
        EmbeddingRecord(
            entity_id="1:2",
            entity_type="function",
            repository_id=1,
            file_path="b.py",
            start_line=10,
            end_line=15,
            text="def normalize_customer(input): ...",
            vector=near,
        )
    )
    store.upsert(
        EmbeddingRecord(
            entity_id="1:3",
            entity_type="function",
            repository_id=1,
            file_path="c.py",
            start_line=3,
            end_line=8,
            text="def render_chart(data): ...",
            vector=far,
        )
    )
    store.save()


def test_duplicate_detector_finds_similar_functions(settings: Settings) -> None:
    seed_similar_vectors(settings)
    detector = DuplicateDetector(settings, threshold=0.85)
    pairs = detector.find_duplicates(repository_id=1, limit=10)
    assert pairs
    assert pairs[0].similarity >= 0.85


def test_refactor_advisor_heuristics(tmp_path: Path) -> None:
    repo = build_repo(tmp_path / "repo")
    analysis = RepositoryAnalyzer().analyze(1, repo)
    advisor = RefactorAdvisor(OllamaClient(Settings()))
    suggestions = advisor.heuristic_suggestions(analysis)
    assert suggestions
