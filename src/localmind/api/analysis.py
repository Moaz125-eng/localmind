from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from localmind.indexing.database import Database
from localmind.indexing.store import IndexStore
from localmind.parsers.analyzer import RepositoryAnalysis, RepositoryAnalyzer


class AnalysisResponse(BaseModel):
    repository_id: int
    module_count: int
    dependency_count: int
    circular_imports: list[list[str]]
    large_functions: list[dict[str, int | str]]
    large_classes: list[dict[str, int | str]]
    graph_nodes: list[str]
    graph_edges: list[dict[str, object]]


def build_analysis_router(database: Database) -> APIRouter:
    router = APIRouter(prefix="/analysis", tags=["analysis"])
    analyzer = RepositoryAnalyzer()

    @router.get("/repositories/{repository_id}", response_model=AnalysisResponse)
    async def analyze_repository(repository_id: int) -> AnalysisResponse:
        async with database.session() as session:
            store = IndexStore(session)
            repository = await store.get_repository_by_id(repository_id)
            if repository is None:
                raise HTTPException(status_code=404, detail="Repository not found")
            result: RepositoryAnalysis = analyzer.analyze(repository_id, Path(repository.root_path))
        return AnalysisResponse(
            repository_id=result.repository_id,
            module_count=result.module_count,
            dependency_count=result.dependency_count,
            circular_imports=result.circular_imports,
            large_functions=result.large_functions,
            large_classes=result.large_classes,
            graph_nodes=result.graph_nodes,
            graph_edges=result.graph_edges,
        )

    return router
