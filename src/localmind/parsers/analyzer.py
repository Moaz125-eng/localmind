from dataclasses import dataclass
from pathlib import Path

from localmind.parsers.import_graph import DependencyGraphBuilder, DependencyReport


@dataclass
class RepositoryAnalysis:
    repository_id: int
    module_count: int
    dependency_count: int
    circular_imports: list[list[str]]
    large_functions: list[dict[str, int | str]]
    large_classes: list[dict[str, int | str]]
    graph_nodes: list[str]
    graph_edges: list[dict[str, object]]


class RepositoryAnalyzer:
    def __init__(self, builder: DependencyGraphBuilder | None = None) -> None:
        self.builder = builder or DependencyGraphBuilder()

    def analyze(self, repository_id: int, root_path: Path) -> RepositoryAnalysis:
        report: DependencyReport = self.builder.build(root_path)
        graph_edges = [
            {"source": edge.source, "target": edge.target, "symbols": edge.symbols}
            for edge in report.edges
        ]
        return RepositoryAnalysis(
            repository_id=repository_id,
            module_count=report.graph.number_of_nodes(),
            dependency_count=report.graph.number_of_edges(),
            circular_imports=report.circular_imports,
            large_functions=report.large_functions,
            large_classes=report.large_classes,
            graph_nodes=list(report.graph.nodes()),
            graph_edges=graph_edges,
        )
