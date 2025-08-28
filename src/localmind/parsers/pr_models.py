from dataclasses import dataclass, field


@dataclass(frozen=True)
class DiffHunk:
    file_path: str
    old_start: int
    new_start: int
    added_lines: int
    removed_lines: int
    content: str


@dataclass
class PullRequestAnalysis:
    files_changed: int
    lines_added: int
    lines_removed: int
    complexity_delta: int
    risky_files: list[str] = field(default_factory=list)
    missing_tests: list[str] = field(default_factory=list)
    duplicate_introductions: list[str] = field(default_factory=list)
    summary: str = ""
