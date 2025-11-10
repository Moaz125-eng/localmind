from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from localmind.indexing.database import Database
from localmind.indexing.doc_service import DocumentationIndexService


class DocChunkResponse(BaseModel):
    id: int
    relative_path: str
    title: str
    kind: str
    start_line: int
    end_line: int
    content: str


class IndexDocsResponse(BaseModel):
    repository_id: int
    files: int
    chunks: int


def build_docs_router(database: Database, exclude_patterns: list[str]) -> APIRouter:
    router = APIRouter(prefix="/docs", tags=["docs"])

    def serialize(record) -> DocChunkResponse:
        return DocChunkResponse(
            id=record.id,
            relative_path=record.relative_path,
            title=record.title,
            kind=record.kind,
            start_line=record.start_line,
            end_line=record.end_line,
            content=record.content,
        )

    @router.post("/repositories/{repository_id}/index", response_model=IndexDocsResponse)
    async def index_docs(repository_id: int) -> IndexDocsResponse:
        async with database.session() as session:
            service = DocumentationIndexService(session, exclude_patterns)
            try:
                stats = await service.index_docs(repository_id)
            except ValueError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            await session.commit()
        return IndexDocsResponse(repository_id=repository_id, files=stats["files"], chunks=stats["chunks"])

    @router.get("/repositories/{repository_id}/chunks", response_model=list[DocChunkResponse])
    async def list_doc_chunks(
        repository_id: int,
        limit: int = Query(default=100, ge=1, le=500),
    ) -> list[DocChunkResponse]:
        async with database.session() as session:
            service = DocumentationIndexService(session, exclude_patterns)
            records = await service.list_chunks(repository_id, limit=limit)
        return [serialize(record) for record in records]

    @router.get("/repositories/{repository_id}/search", response_model=list[DocChunkResponse])
    async def search_doc_chunks(
        repository_id: int,
        query: str = Query(min_length=1),
        limit: int = Query(default=20, ge=1, le=100),
    ) -> list[DocChunkResponse]:
        async with database.session() as session:
            service = DocumentationIndexService(session, exclude_patterns)
            records = await service.search_chunks(repository_id, query, limit=limit)
        return [serialize(record) for record in records]

    return router
