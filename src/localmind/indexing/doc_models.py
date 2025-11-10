from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from localmind.indexing.models import Base


class DocChunkKind(StrEnum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    CODE = "code"


class DocChunkRecord(Base):
    __tablename__ = "doc_chunks"
    __table_args__ = (
        UniqueConstraint("repository_id", "relative_path", "start_line", name="uq_doc_chunk"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), index=True)
    relative_path: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(32))
    start_line: Mapped[int] = mapped_column(Integer)
    end_line: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    indexed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
