from localmind.rag.models import RetrievedChunk
from localmind.search.models import SearchResult


class ContextChunker:
    MAX_CHUNK_CHARS = 1200

    def build_chunks(self, results: list[SearchResult]) -> list[RetrievedChunk]:
        chunks: list[RetrievedChunk] = []
        for result in results:
            content = result.snippet.strip()
            if not content:
                continue
            if len(content) > self.MAX_CHUNK_CHARS:
                content = content[: self.MAX_CHUNK_CHARS]
            chunks.append(
                RetrievedChunk(
                    file_path=result.file_path,
                    start_line=result.start_line,
                    end_line=result.end_line,
                    score=result.score,
                    content=content,
                )
            )
        return chunks

    def merge_chunks(self, chunks: list[RetrievedChunk], max_chunks: int = 6) -> str:
        selected = chunks[:max_chunks]
        blocks: list[str] = []
        for chunk in selected:
            header = f"[{chunk.file_path}:{chunk.start_line}-{chunk.end_line}] score={chunk.score:.2f}"
            blocks.append(f"{header}\n{chunk.content}")
        return "\n\n".join(blocks)
