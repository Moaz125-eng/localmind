from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from localmind.indexing.database import Database
from localmind.indexing.store import IndexStore
from localmind.parsers.analyzer import RepositoryAnalysis, RepositoryAnalyzer
from localmind.parsers.call_graph import CallGraphBuilder


class AnalysisResponse(BaseModel):
    repository_id: int
    module_count: int
    dependency_count: int
    circular_imports: list[list[str]]
    large_functions: list[dict[str, int | str]]
    large_classes: list[dict[str, int | str]]
    graph_nodes: list[str]
    graph_edges: list[dict[str, object]]


class CallGraphResponse(BaseModel):
    repository_id: int
    function_count: int
    edge_count: int
    entry_points: list[str]
    edges: list[dict[str, object]]
    nodes: list[str]


def build_analysis_router(database: Database) -> APIRouter:
    router = APIRouter(prefix="/analysis", tags=["analysis"])
    analyzer = RepositoryAnalyzer()
    call_graph_builder = CallGraphBuilder()

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

    @router.get("/repositories/{repository_id}/call-graph", response_model=CallGraphResponse)
    async def call_graph(repository_id: int) -> CallGraphResponse:
        async with database.session() as session:
            store = IndexStore(session)
            repository = await store.get_repository_by_id(repository_id)
            if repository is None:
                raise HTTPException(status_code=404, detail="Repository not found")
            report = call_graph_builder.build(Path(repository.root_path))
            payload = call_graph_builder.to_payload(report)
        return CallGraphResponse(
            repository_id=repository_id,
            function_count=int(payload["function_count"]),
            edge_count=int(payload["edge_count"]),
            entry_points=list(payload["entry_points"]),
            edges=list(payload["edges"]),
            nodes=list(payload["nodes"]),
        )

    @router.get("/repositories/{repository_id}/call-graph/filter")
    async def filter_call_graph(repository_id: int, prefix: str) -> dict[str, object]:
        async with database.session() as session:
            store = IndexStore(session)
            repository = await store.get_repository_by_id(repository_id)
            if repository is None:
                raise HTTPException(status_code=404, detail="Repository not found")
            report = call_graph_builder.build(Path(repository.root_path))
            return call_graph_builder.filter_by_prefix(report, prefix)

    return router
