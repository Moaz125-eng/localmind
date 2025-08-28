from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx

from localmind.parsers.import_graph import DependencyGraphBuilder


@dataclass(frozen=True)
class GraphExport:
    format: str
    path: Path


class ArchitectureVisualizer:
    def __init__(self, builder: DependencyGraphBuilder | None = None) -> None:
        self.builder = builder or DependencyGraphBuilder()

    def render_import_graph(
        self,
        root_path: Path,
        output_dir: Path,
        filename: str = "import_graph",
        layout: str = "spring",
    ) -> list[GraphExport]:
        output_dir.mkdir(parents=True, exist_ok=True)
        report = self.builder.build(root_path)
        graph = report.graph
        if graph.number_of_nodes() == 0:
            return []

        pos = nx.spring_layout(graph) if layout == "spring" else nx.kamada_kawai_layout(graph)
        plt.figure(figsize=(12, 8))
        nx.draw_networkx_nodes(graph, pos, node_size=700, node_color="#5B8DEF")
        nx.draw_networkx_edges(graph, pos, edge_color="#666666", arrows=True)
        nx.draw_networkx_labels(graph, pos, font_size=8)
        png_path = output_dir / f"{filename}.png"
        svg_path = output_dir / f"{filename}.svg"
        plt.tight_layout()
        plt.savefig(png_path, format="png")
        plt.savefig(svg_path, format="svg")
        plt.close()
        return [GraphExport(format="png", path=png_path), GraphExport(format="svg", path=svg_path)]

    def graph_summary(self, root_path: Path) -> dict[str, object]:
        report = self.builder.build(root_path)
        degrees = dict(report.graph.degree())
        top_nodes = sorted(degrees.items(), key=lambda item: item[1], reverse=True)[:10]
        return {
            "module_count": report.graph.number_of_nodes(),
            "edge_count": report.graph.number_of_edges(),
            "circular_imports": report.circular_imports,
            "top_dependencies": [{"module": module, "degree": degree} for module, degree in top_nodes],
        }

    def filter_graph(self, root_path: Path, module_prefix: str) -> dict[str, object]:
        report = self.builder.build(root_path)
        filtered = report.graph.subgraph(
            [node for node in report.graph.nodes if node.startswith(module_prefix)]
        ).copy()
        return {
            "module_prefix": module_prefix,
            "nodes": list(filtered.nodes()),
            "edges": [{"source": u, "target": v} for u, v in filtered.edges()],
        }
