from dataclasses import dataclass


@dataclass(frozen=True)
class SearchResult:
    entity_id: str
    score: float
    file_path: str
    start_line: int
    end_line: int
    entity_type: str
    snippet: str
    repository_id: int
