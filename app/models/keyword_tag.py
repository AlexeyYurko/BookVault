from sqlalchemy import String
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.db.annotations import int_pk
from app.db.base import Base


class KeywordTag(Base):
    __tablename__ = "keyword_tags"

    id: Mapped[int_pk]
    keyword: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)

    def __repr__(self):
        return f"KeywordTag(id={self.id}, keyword=\"{self.keyword}\")"
