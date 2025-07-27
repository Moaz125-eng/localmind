from dataclasses import dataclass, field
from pathlib import Path

import networkx as nx

from localmind.parsers.python_ast import ModuleAnalysis, PythonModuleAnalyzer


@dataclass
class DependencyEdge:
    source: str
    target: str
    symbols: list[str] = field(default_factory=list)


@dataclass
class DependencyReport:
    graph: nx.DiGraph
    edges: list[DependencyEdge]
    circular_imports: list[list[str]]
    large_functions: list[dict[str, int | str]]
    large_classes: list[dict[str, int | str]]


class DependencyGraphBuilder:
    FUNCTION_LINE_THRESHOLD = 80
    CLASS_LINE_THRESHOLD = 120

    def __init__(self, analyzer: PythonModuleAnalyzer | None = None) -> None:
        self.analyzer = analyzer or PythonModuleAnalyzer()

    def build(self, root_path: Path) -> DependencyReport:
        graph = nx.DiGraph()
        edges: list[DependencyEdge] = []
        analyses: dict[str, ModuleAnalysis] = {}

        python_files = sorted(root_path.rglob("*.py"))
        module_map = {self._module_name(root_path, path): path for path in python_files}

        for module_name, file_path in module_map.items():
            graph.add_node(module_name)
            analysis = self.analyzer.analyze_file(file_path)
            analyses[module_name] = analysis
            for import_ref in analysis.imports:
                target = self._resolve_target(module_name, import_ref.module, import_ref.level, module_map)
                if target is None:
                    continue
                graph.add_edge(module_name, target, symbols=import_ref.names)
                edges.append(DependencyEdge(source=module_name, target=target, symbols=import_ref.names))

        circular = [list(cycle) for cycle in nx.simple_cycles(graph)]
        large_functions: list[dict[str, int | str]] = []
        large_classes: list[dict[str, int | str]] = []

        for module_name, analysis in analyses.items():
            for function in analysis.functions:
                if function.line_count >= self.FUNCTION_LINE_THRESHOLD:
                    large_functions.append(
                        {
                            "module": module_name,
                            "name": function.name,
                            "lines": function.line_count,
                            "complexity": function.complexity,
                            "start_line": function.start_line,
                        }
                    )
            for class_metric in analysis.classes:
                if class_metric.line_count >= self.CLASS_LINE_THRESHOLD:
                    large_classes.append(
                        {
                            "module": module_name,
                            "name": class_metric.name,
                            "lines": class_metric.line_count,
                            "methods": class_metric.method_count,
                            "start_line": class_metric.start_line,
                        }
                    )

        return DependencyReport(
            graph=graph,
            edges=edges,
            circular_imports=circular,
            large_functions=sorted(large_functions, key=lambda item: int(item["lines"]), reverse=True),
            large_classes=sorted(large_classes, key=lambda item: int(item["lines"]), reverse=True),
        )

    def _module_name(self, root_path: Path, file_path: Path) -> str:
        relative = file_path.relative_to(root_path)
        parts = list(relative.with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts) if parts else relative.stem

    def _resolve_target(
        self,
        source_module: str,
        imported_module: str,
        level: int,
        module_map: dict[str, Path],
    ) -> str | None:
        if level:
            source_parts = source_module.split(".")
            prefix_parts = source_parts[: max(len(source_parts) - level, 0)]
            if imported_module:
                candidate = ".".join(prefix_parts + imported_module.split("."))
            else:
                candidate = ".".join(prefix_parts)
        else:
            candidate = imported_module
        if candidate in module_map:
            return candidate
        for module_name in module_map:
            if module_name.endswith(candidate) or candidate.endswith(module_name):
                return module_name
        return None
