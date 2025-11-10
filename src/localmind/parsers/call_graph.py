import ast
from dataclasses import dataclass, field
from pathlib import Path

import networkx as nx


@dataclass(frozen=True)
class CallEdge:
    caller: str
    callee: str
    line: int


@dataclass
class CallGraphReport:
    graph: nx.DiGraph
    edges: list[CallEdge] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)


class CallGraphBuilder:
    BUILTIN_CALLS = {"print", "len", "range", "str", "int", "float", "bool", "list", "dict", "set"}

    def build(self, root_path: Path) -> CallGraphReport:
        graph = nx.DiGraph()
        edges: list[CallEdge] = []
        functions: set[str] = set()
        python_files = sorted(root_path.rglob("*.py"))

        for file_path in python_files:
            module = self._module_name(root_path, file_path)
            source = file_path.read_text(encoding="utf-8", errors="replace")
            try:
                tree = ast.parse(source, filename=str(file_path))
            except SyntaxError:
                continue
            module_functions = self._module_functions(tree, module)
            functions.update(module_functions.keys())
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    caller = f"{module}.{node.name}"
                    graph.add_node(caller, kind="function", path=str(file_path))
                    for call in self._collect_calls(node):
                        callee = self._resolve_callee(call, module, module_functions)
                        if callee is None:
                            continue
                        graph.add_node(callee, kind="function")
                        graph.add_edge(caller, callee, line=call.lineno)
                        edges.append(CallEdge(caller=caller, callee=callee, line=call.lineno))

        in_degree = dict(graph.in_degree())
        entry_points = sorted(
            node for node in graph.nodes if in_degree.get(node, 0) == 0 and graph.out_degree(node) > 0
        )
        return CallGraphReport(
            graph=graph,
            edges=edges,
            functions=sorted(functions),
            entry_points=entry_points,
        )

    def _module_name(self, root_path: Path, file_path: Path) -> str:
        relative = file_path.relative_to(root_path)
        parts = list(relative.with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts) if parts else relative.stem

    def _module_functions(self, tree: ast.AST, module: str) -> dict[str, str]:
        mapping: dict[str, str] = {}
        if not isinstance(tree, ast.Module):
            return mapping
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                mapping[node.name] = f"{module}.{node.name}"
        return mapping

    def _collect_calls(self, node: ast.AST) -> list[ast.Call]:
        calls: list[ast.Call] = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                calls.append(child)
        return calls

    def _resolve_callee(
        self,
        call: ast.Call,
        module: str,
        module_functions: dict[str, str],
    ) -> str | None:
        func = call.func
        if isinstance(func, ast.Name):
            name = func.id
            if name in self.BUILTIN_CALLS:
                return None
            if name in module_functions:
                return module_functions[name]
            return f"{module}.{name}"
        if isinstance(func, ast.Attribute):
            if isinstance(func.value, ast.Name):
                base = func.value.id
                attr = func.attr
                if base in module_functions:
                    return f"{module_functions[base]}.{attr}"
                return f"{base}.{attr}"
        return None

    def to_payload(self, report: CallGraphReport) -> dict[str, object]:
        return {
            "function_count": len(report.functions),
            "edge_count": len(report.edges),
            "entry_points": report.entry_points,
            "edges": [
                {"caller": edge.caller, "callee": edge.callee, "line": edge.line}
                for edge in report.edges
            ],
            "nodes": list(report.graph.nodes()),
        }

    def filter_by_prefix(self, report: CallGraphReport, prefix: str) -> dict[str, object]:
        filtered = report.graph.subgraph(
            [node for node in report.graph.nodes if str(node).startswith(prefix)]
        ).copy()
        return {
            "prefix": prefix,
            "nodes": list(filtered.nodes()),
            "edges": [
                {"caller": caller, "callee": callee, "line": data.get("line", 0)}
                for caller, callee, data in filtered.edges(data=True)
            ],
        }
