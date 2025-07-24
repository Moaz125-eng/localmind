import ast
from dataclasses import dataclass

from localmind.indexing.models import FileRecord, SymbolRecord


@dataclass(frozen=True)
class ParsedSymbol:
    name: str
    kind: str
    start_line: int
    end_line: int
    docstring: str | None


class PythonSymbolExtractor:
    def extract(self, source: str) -> list[ParsedSymbol]:
        tree = ast.parse(source)
        symbols: list[ParsedSymbol] = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                symbols.append(
                    ParsedSymbol(
                        name=node.name,
                        kind="class",
                        start_line=node.lineno,
                        end_line=node.end_lineno or node.lineno,
                        docstring=ast.get_docstring(node),
                    )
                )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                symbols.append(
                    ParsedSymbol(
                        name=node.name,
                        kind="function",
                        start_line=node.lineno,
                        end_line=node.end_lineno or node.lineno,
                        docstring=ast.get_docstring(node),
                    )
                )
        return symbols

    def build_records(self, file_record: FileRecord, source: str) -> list[SymbolRecord]:
        return [
            SymbolRecord(
                file_id=file_record.id,
                name=symbol.name,
                kind=symbol.kind,
                start_line=symbol.start_line,
                end_line=symbol.end_line,
                docstring=symbol.docstring,
            )
            for symbol in self.extract(source)
        ]
