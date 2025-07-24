from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class IndexStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RepositoryRecord(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    root_path: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default=IndexStatus.PENDING.value)
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    files: Mapped[list["FileRecord"]] = relationship(back_populates="repository")


class FileRecord(Base):
    __tablename__ = "files"
    __table_args__ = (UniqueConstraint("repository_id", "relative_path", name="uq_repo_path"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), index=True)
    relative_path: Mapped[str] = mapped_column(Text)
    absolute_path: Mapped[str] = mapped_column(Text)
    extension: Mapped[str] = mapped_column(String(32))
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    content_hash: Mapped[str] = mapped_column(String(64))
    modified_at: Mapped[datetime] = mapped_column(DateTime)
    indexed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    repository: Mapped[RepositoryRecord] = relationship(back_populates="files")
    symbols: Mapped[list["SymbolRecord"]] = relationship(back_populates="file")


class SymbolRecord(Base):
    __tablename__ = "symbols"
    __table_args__ = (UniqueConstraint("file_id", "name", "kind", "start_line", name="uq_symbol"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(32))
    start_line: Mapped[int] = mapped_column(Integer)
    end_line: Mapped[int] = mapped_column(Integer)
    docstring: Mapped[str | None] = mapped_column(Text, nullable=True)

    file: Mapped[FileRecord] = relationship(back_populates="symbols")
