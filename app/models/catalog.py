import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.annotations import int_pk
from app.db.base import Base


class CatalogKind(enum.StrEnum):
    book = enum.auto()
    magazine = enum.auto()


class Catalog(Base):
    __tablename__ = "catalogs"

    id: Mapped[int_pk]
    name: Mapped[str] = mapped_column(String, nullable=False)
    root_path: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    kind: Mapped[str] = mapped_column(String, nullable=False, default=CatalogKind.book.value)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    books: Mapped[list["Book"]] = relationship(back_populates="catalog")

    def __repr__(self) -> str:
        return f"Catalog(id={self.id}, name={self.name!r}, root_path={self.root_path!r})"


from app.models.books import Book  # noqa: E402
