from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from localmind.indexing.models import Base


class SavedSearchRecord(Base):
    __tablename__ = "saved_searches"
    __table_args__ = (UniqueConstraint("name", "repository_id", name="uq_saved_search"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    query: Mapped[str] = mapped_column(Text)
    repository_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    min_score: Mapped[int] = mapped_column(Integer, default=20)
    result_limit: Mapped[int] = mapped_column(Integer, default=10)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
