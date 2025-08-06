from dataclasses import dataclass


@dataclass(frozen=True)
class DuplicatePair:
    left_entity_id: str
    right_entity_id: str
    similarity: float
    left_file: str
    right_file: str
    left_start_line: int
    right_start_line: int
    left_snippet: str
    right_snippet: str
