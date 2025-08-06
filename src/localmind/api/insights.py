from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from localmind.core.settings import Settings
from localmind.indexing.database import Database
from localmind.indexing.store import IndexStore
from localmind.parsers.analyzer import RepositoryAnalyzer
from localmind.rag.ollama import OllamaClient
from localmind.rag.refactor import RefactorAdvisor
from localmind.search.duplicate_service import DuplicateDetector
from localmind.search.duplicates import DuplicatePair


class DuplicateResponse(BaseModel):
    left_entity_id: str
    right_entity_id: str
    similarity: float
    left_file: str
    right_file: str
    left_start_line: int
    right_start_line: int
    left_snippet: str
    right_snippet: str


class RefactorSuggestionResponse(BaseModel):
    title: str
    severity: str
    rationale: str
    before: str
    after: str


class RefactorReportResponse(BaseModel):
    repository_id: int
    markdown_report: str
    suggestions: list[RefactorSuggestionResponse]


def build_insights_router(database: Database, settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/insights", tags=["insights"])
    detector = DuplicateDetector(settings)
    analyzer = RepositoryAnalyzer()
    advisor = RefactorAdvisor(OllamaClient(settings))

    def serialize_duplicate(item: DuplicatePair) -> DuplicateResponse:
        return DuplicateResponse(
            left_entity_id=item.left_entity_id,
            right_entity_id=item.right_entity_id,
            similarity=item.similarity,
            left_file=item.left_file,
            right_file=item.right_file,
            left_start_line=item.left_start_line,
            right_start_line=item.right_start_line,
            left_snippet=item.left_snippet,
            right_snippet=item.right_snippet,
        )

    @router.get("/duplicates", response_model=list[DuplicateResponse])
    async def list_duplicates(
        repository_id: int | None = None,
        threshold: float = Query(default=0.88, ge=0.5, le=1.0),
        limit: int = Query(default=25, ge=1, le=100),
    ) -> list[DuplicateResponse]:
        detector.threshold = threshold
        pairs = detector.find_duplicates(repository_id=repository_id, limit=limit)
        return [serialize_duplicate(item) for item in pairs]

    @router.get("/refactors/{repository_id}", response_model=RefactorReportResponse)
    async def refactor_report(repository_id: int) -> RefactorReportResponse:
        async with database.session() as session:
            store = IndexStore(session)
            repository = await store.get_repository_by_id(repository_id)
            if repository is None:
                raise HTTPException(status_code=404, detail="Repository not found")
            analysis = analyzer.analyze(repository_id, Path(repository.root_path))
        suggestions = advisor.heuristic_suggestions(analysis)
        markdown = await advisor.generate_report(analysis, {})
        return RefactorReportResponse(
            repository_id=repository_id,
            markdown_report=markdown,
            suggestions=[
                RefactorSuggestionResponse(
                    title=item.title,
                    severity=item.severity,
                    rationale=item.rationale,
                    before=item.before,
                    after=item.after,
                )
                for item in suggestions
            ],
        )

    return router
