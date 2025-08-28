from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from localmind.core.settings import Settings
from localmind.indexing.database import Database
from localmind.indexing.store import IndexStore
from localmind.parsers.pr_analyzer import PullRequestAnalyzer
from localmind.parsers.pr_models import PullRequestAnalysis
from localmind.visualization.graphs import ArchitectureVisualizer


class PullRequestRequest(BaseModel):
    diff_text: str = Field(min_length=1)


class PullRequestResponse(BaseModel):
    files_changed: int
    lines_added: int
    lines_removed: int
    complexity_delta: int
    risky_files: list[str]
    missing_tests: list[str]
    duplicate_introductions: list[str]
    summary: str


class GraphExportResponse(BaseModel):
    format: str
    path: str


def build_review_router(database: Database, settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/review", tags=["review"])
    pr_analyzer = PullRequestAnalyzer()
    visualizer = ArchitectureVisualizer()

    def serialize(analysis: PullRequestAnalysis) -> PullRequestResponse:
        return PullRequestResponse(
            files_changed=analysis.files_changed,
            lines_added=analysis.lines_added,
            lines_removed=analysis.lines_removed,
            complexity_delta=analysis.complexity_delta,
            risky_files=analysis.risky_files,
            missing_tests=analysis.missing_tests,
            duplicate_introductions=analysis.duplicate_introductions,
            summary=analysis.summary,
        )

    @router.post("/pull-request", response_model=PullRequestResponse)
    async def analyze_pull_request(payload: PullRequestRequest) -> PullRequestResponse:
        result = pr_analyzer.analyze(payload.diff_text)
        return serialize(result)

    @router.get("/repositories/{repository_id}/architecture")
    async def architecture_summary(repository_id: int) -> dict[str, object]:
        async with database.session() as session:
            store = IndexStore(session)
            repository = await store.get_repository_by_id(repository_id)
            if repository is None:
                raise HTTPException(status_code=404, detail="Repository not found")
            return visualizer.graph_summary(Path(repository.root_path))

    @router.post("/repositories/{repository_id}/architecture/export", response_model=list[GraphExportResponse])
    async def export_architecture(repository_id: int) -> list[GraphExportResponse]:
        async with database.session() as session:
            store = IndexStore(session)
            repository = await store.get_repository_by_id(repository_id)
            if repository is None:
                raise HTTPException(status_code=404, detail="Repository not found")
            exports = visualizer.render_import_graph(
                Path(repository.root_path),
                settings.data_dir / "graphs" / str(repository_id),
            )
        return [GraphExportResponse(format=item.format, path=str(item.path)) for item in exports]

    @router.get("/repositories/{repository_id}/architecture/filter")
    async def filter_architecture(repository_id: int, module_prefix: str) -> dict[str, object]:
        async with database.session() as session:
            store = IndexStore(session)
            repository = await store.get_repository_by_id(repository_id)
            if repository is None:
                raise HTTPException(status_code=404, detail="Repository not found")
            return visualizer.filter_graph(Path(repository.root_path), module_prefix)

    return router
