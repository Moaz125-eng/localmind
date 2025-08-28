import re
from pathlib import Path

from localmind.parsers.pr_models import DiffHunk, PullRequestAnalysis
from localmind.parsers.python_ast import PythonModuleAnalyzer


class GitDiffParser:
    HUNK_PATTERN = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")

    def parse(self, diff_text: str) -> list[DiffHunk]:
        hunks: list[DiffHunk] = []
        current_file = ""
        current_hunk_lines: list[str] = []
        old_start = 0
        new_start = 0

        for line in diff_text.splitlines():
            if line.startswith("diff --git"):
                current_file = line.split()[-1].removeprefix("b/")
                continue
            match = self.HUNK_PATTERN.match(line)
            if match:
                if current_hunk_lines and current_file:
                    hunks.append(self._build_hunk(current_file, old_start, new_start, current_hunk_lines))
                new_start = int(match.group(1))
                old_start = new_start
                current_hunk_lines = [line]
                continue
            if current_hunk_lines is not None and line.startswith(("+", "-", " ")):
                current_hunk_lines.append(line)

        if current_hunk_lines and current_file:
            hunks.append(self._build_hunk(current_file, old_start, new_start, current_hunk_lines))
        return hunks

    def _build_hunk(self, file_path: str, old_start: int, new_start: int, lines: list[str]) -> DiffHunk:
        added = sum(1 for line in lines if line.startswith("+") and not line.startswith("+++"))
        removed = sum(1 for line in lines if line.startswith("-") and not line.startswith("---"))
        return DiffHunk(
            file_path=file_path,
            old_start=old_start,
            new_start=new_start,
            added_lines=added,
            removed_lines=removed,
            content="\n".join(lines),
        )


class PullRequestAnalyzer:
    RISK_LINE_THRESHOLD = 120

    def __init__(self, parser: GitDiffParser | None = None) -> None:
        self.parser = parser or GitDiffParser()
        self.module_analyzer = PythonModuleAnalyzer()

    def analyze(self, diff_text: str, repository_root: Path | None = None) -> PullRequestAnalysis:
        hunks = self.parser.parse(diff_text)
        files = {hunk.file_path for hunk in hunks}
        added = sum(hunk.added_lines for hunk in hunks)
        removed = sum(hunk.removed_lines for hunk in hunks)
        risky_files: list[str] = []
        missing_tests: list[str] = []
        duplicate_introductions: list[str] = []
        complexity_delta = 0

        for hunk in hunks:
            if hunk.added_lines - hunk.removed_lines > self.RISK_LINE_THRESHOLD:
                risky_files.append(hunk.file_path)
            if hunk.file_path.endswith(".py") and not hunk.file_path.startswith("tests/"):
                test_candidate = f"tests/test_{Path(hunk.file_path).stem}.py"
                if repository_root is not None:
                    if not (repository_root / test_candidate).exists():
                        missing_tests.append(test_candidate)
                else:
                    missing_tests.append(test_candidate)
            added_python = self._extract_added_python(hunk.content)
            if added_python:
                complexity_delta += self._estimate_complexity(added_python)
            if self._looks_duplicated(hunk.content):
                duplicate_introductions.append(hunk.file_path)

        summary = (
            f"Changed {len(files)} files with +{added}/-{removed} lines. "
            f"Complexity delta ~{complexity_delta}. "
            f"Risky files: {len(risky_files)}."
        )
        return PullRequestAnalysis(
            files_changed=len(files),
            lines_added=added,
            lines_removed=removed,
            complexity_delta=complexity_delta,
            risky_files=risky_files,
            missing_tests=sorted(set(missing_tests)),
            duplicate_introductions=sorted(set(duplicate_introductions)),
            summary=summary,
        )

    def _extract_added_python(self, hunk_content: str) -> str:
        lines = [
            line[1:]
            for line in hunk_content.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        ]
        return "\n".join(lines)

    def _estimate_complexity(self, source: str) -> int:
        if not source.strip():
            return 0
        try:
            import ast

            tree = ast.parse(source)
            analyzer = PythonModuleAnalyzer()
            functions = analyzer._collect_functions(tree)
            return sum(function.complexity for function in functions)
        except SyntaxError:
            return 1

    def _looks_duplicated(self, hunk_content: str) -> bool:
        added_lines = [
            line[1:].strip()
            for line in hunk_content.splitlines()
            if line.startswith("+") and line.strip() not in {"+", "++"}
        ]
        return len(set(added_lines)) < max(len(added_lines) // 2, 1) and len(added_lines) >= 4
