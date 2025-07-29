from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class EmbeddingRecord:
    entity_id: str
    entity_type: str
    repository_id: int
    file_path: str
    start_line: int
    end_line: int
    text: str
    vector: np.ndarray


class SentenceTransformerEncoder:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def dimension(self) -> int:
        model = self._load_model()
        return int(model.get_sentence_embedding_dimension())

    def encode_batch(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)
        model = self._load_model()
        vectors = model.encode(texts, batch_size=batch_size, show_progress_bar=False)
        return np.asarray(vectors, dtype=np.float32)
