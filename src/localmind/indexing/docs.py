import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from localmind.indexing.doc_models import DocChunkKind, DocChunkRecord


@dataclass(frozen=True)
class ParsedDocChunk:
    relative_path: str
    title: str
    kind: str
    start_line: int
    end_line: int
    content: str
    content_hash: str


class MarkdownChunkParser:
    HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$")
    CODE_FENCE = re.compile(r"^```")

    def parse_file(self, root_path: Path, file_path: Path) -> list[ParsedDocChunk]:
        relative = str(file_path.relative_to(root_path))
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        chunks: list[ParsedDocChunk] = []
        current_title = Path(relative).stem
        paragraph_lines: list[str] = []
        paragraph_start = 1
        in_code = False
        code_lines: list[str] = []
        code_start = 0

        def flush_paragraph(end_line: int) -> None:
            nonlocal paragraph_lines, paragraph_start
            if not paragraph_lines:
                return
            content = "\n".join(paragraph_lines).strip()
            if content:
                chunks.append(self._chunk(relative, current_title, DocChunkKind.PARAGRAPH.value, paragraph_start, end_line, content))
            paragraph_lines = []

        for index, line in enumerate(lines, start=1):
            if self.CODE_FENCE.match(line.strip()):
                if in_code:
                    content = "\n".join(code_lines).strip()
                    if content:
                        chunks.append(
                            self._chunk(
                                relative,
                                current_title,
                                DocChunkKind.CODE.value,
                                code_start,
                                index,
                                content,
                            )
                        )
                    code_lines = []
                    in_code = False
                else:
                    flush_paragraph(index - 1)
                    in_code = True
                    code_start = index
                continue

            if in_code:
                code_lines.append(line)
                continue

            heading = self.HEADING_PATTERN.match(line)
            if heading:
                flush_paragraph(index - 1)
                current_title = heading.group(2).strip()
                chunks.append(
                    self._chunk(
                        relative,
                        current_title,
                        DocChunkKind.HEADING.value,
                        index,
                        index,
                        line.strip(),
                    )
                )
                paragraph_start = index + 1
                continue

            if not line.strip():
                flush_paragraph(index)
                paragraph_start = index + 1
                continue

            if not paragraph_lines:
                paragraph_start = index
            paragraph_lines.append(line)

        flush_paragraph(len(lines))
        return chunks

    def _chunk(
        self,
        relative_path: str,
        title: str,
        kind: str,
        start_line: int,
        end_line: int,
        content: str,
    ) -> ParsedDocChunk:
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return ParsedDocChunk(
            relative_path=relative_path,
            title=title,
            kind=kind,
            start_line=start_line,
            end_line=end_line,
            content=content,
            content_hash=digest,
        )


class DocumentationIndexer:
    MARKDOWN_EXTENSIONS = {".md", ".markdown", ".mdx"}

    def __init__(self, parser: MarkdownChunkParser | None = None) -> None:
        self.parser = parser or MarkdownChunkParser()

    def scan(self, root_path: Path, exclude_patterns: list[str]) -> list[ParsedDocChunk]:
        discovered: list[ParsedDocChunk] = []
        for path in sorted(root_path.rglob("*")):
            if not path.is_file() or path.suffix not in self.MARKDOWN_EXTENSIONS:
                continue
            relative = path.relative_to(root_path)
            if any(pattern in relative.parts for pattern in exclude_patterns):
                continue
            discovered.extend(self.parser.parse_file(root_path, path))
        return discovered

    def to_records(self, repository_id: int, chunks: list[ParsedDocChunk]) -> list[DocChunkRecord]:
        return [
            DocChunkRecord(
                repository_id=repository_id,
                relative_path=chunk.relative_path,
                title=chunk.title,
                kind=chunk.kind,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                content=chunk.content,
                content_hash=chunk.content_hash,
            )
            for chunk in chunks
        ]
