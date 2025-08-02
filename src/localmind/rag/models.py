from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievedChunk:
    file_path: str
    start_line: int
    end_line: int
    score: float
    content: str


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str
