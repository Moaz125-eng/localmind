import ast
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ImportReference:
    module: str
    names: list[str]
    line: int
    level: int = 0


@dataclass
class FunctionMetrics:
    name: str
    start_line: int
    end_line: int
    complexity: int
    line_count: int


@dataclass
class ClassMetrics:
    name: str
    start_line: int
    end_line: int
    method_count: int
    line_count: int


@dataclass
class ModuleAnalysis:
    path: str
    imports: list[ImportReference] = field(default_factory=list)
    functions: list[FunctionMetrics] = field(default_factory=list)
    classes: list[ClassMetrics] = field(default_factory=list)


class PythonModuleAnalyzer:
    def analyze_file(self, path: Path) -> ModuleAnalysis:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(path))
        return ModuleAnalysis(
            path=str(path),
            imports=self._collect_imports(tree),
            functions=self._collect_functions(tree),
            classes=self._collect_classes(tree),
        )

    def _collect_imports(self, tree: ast.AST) -> list[ImportReference]:
        imports: list[ImportReference] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(
                        ImportReference(module=alias.name, names=[alias.asname or alias.name], line=node.lineno)
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = [alias.name for alias in node.names]
                imports.append(
                    ImportReference(module=module, names=names, line=node.lineno, level=node.level)
                )
        return imports

    def _collect_functions(self, tree: ast.AST) -> list[FunctionMetrics]:
        functions: list[FunctionMetrics] = []
        for node in tree.body if isinstance(tree, ast.Module) else []:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end_line = node.end_lineno or node.lineno
                functions.append(
                    FunctionMetrics(
                        name=node.name,
                        start_line=node.lineno,
                        end_line=end_line,
                        complexity=self._complexity(node),
                        line_count=end_line - node.lineno + 1,
                    )
                )
        return functions

    def _collect_classes(self, tree: ast.AST) -> list[ClassMetrics]:
        classes: list[ClassMetrics] = []
        for node in tree.body if isinstance(tree, ast.Module) else []:
            if isinstance(node, ast.ClassDef):
                end_line = node.end_lineno or node.lineno
                method_count = sum(
                    1
                    for child in node.body
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                )
                classes.append(
                    ClassMetrics(
                        name=node.name,
                        start_line=node.lineno,
                        end_line=end_line,
                        method_count=method_count,
                        line_count=end_line - node.lineno + 1,
                    )
                )
        return classes

    def _complexity(self, node: ast.AST) -> int:
        score = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith)):
                score += 1
            elif isinstance(child, ast.BoolOp):
                score += max(len(child.values) - 1, 0)
            elif isinstance(child, (ast.ExceptHandler, ast.comprehension)):
                score += 1
        return score
