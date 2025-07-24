import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class ScannedFile:
    relative_path: str
    absolute_path: Path
    extension: str
    size_bytes: int
    content_hash: str
    modified_at: datetime


class RepositoryScanner:
    PYTHON_EXTENSIONS = {".py", ".pyi"}

    def __init__(self, root_path: Path, exclude_patterns: list[str]) -> None:
        self.root_path = root_path.resolve()
        self.exclude_patterns = exclude_patterns

    def should_skip(self, path: Path) -> bool:
        parts = set(path.parts)
        for pattern in self.exclude_patterns:
            if pattern in parts:
                return True
        return False

    def scan(self) -> list[ScannedFile]:
        if not self.root_path.exists():
            raise FileNotFoundError(f"Repository path not found: {self.root_path}")

        discovered: list[ScannedFile] = []
        for path in self.root_path.rglob("*"):
            if not path.is_file():
                continue
            if self.should_skip(path.relative_to(self.root_path)):
                continue
            if path.suffix not in self.PYTHON_EXTENSIONS:
                continue
            stat = path.stat()
            content = path.read_bytes()
            discovered.append(
                ScannedFile(
                    relative_path=str(path.relative_to(self.root_path)),
                    absolute_path=path,
                    extension=path.suffix,
                    size_bytes=stat.st_size,
                    content_hash=hashlib.sha256(content).hexdigest(),
                    modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                )
            )
        discovered.sort(key=lambda item: item.relative_path)
        return discovered
