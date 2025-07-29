from localmind.core.settings import Settings
from localmind.embeddings.encoder import SentenceTransformerEncoder
from localmind.embeddings.store import FaissVectorStore
from localmind.search.models import SearchResult


class SemanticSearchEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.encoder = SentenceTransformerEncoder(settings.embedding_model)
        self.vector_store = FaissVectorStore(
            settings.data_dir / "vectors" / "symbols.faiss",
            dimension=self.encoder.dimension,
        )

    def search(
        self,
        query: str,
        repository_id: int | None = None,
        limit: int = 10,
        min_score: float = 0.2,
    ) -> list[SearchResult]:
        query_vector = self.encoder.encode_batch([query])[0]
        hits = self.vector_store.search(query_vector, limit=limit * 3)
        results: list[SearchResult] = []
        for hit in hits:
            if hit.score < min_score:
                continue
            metadata = hit.metadata
            if repository_id is not None and metadata.get("repository_id") != repository_id:
                continue
            text = str(metadata.get("text", ""))
            snippet = text.split("\n", maxsplit=2)[-1][:400]
            results.append(
                SearchResult(
                    entity_id=hit.entity_id,
                    score=hit.score,
                    file_path=str(metadata.get("file_path", "")),
                    start_line=int(metadata.get("start_line", 0)),
                    end_line=int(metadata.get("end_line", 0)),
                    entity_type=str(metadata.get("entity_type", "")),
                    snippet=snippet,
                    repository_id=int(metadata.get("repository_id", 0)),
                )
            )
            if len(results) >= limit:
                break
        return results
