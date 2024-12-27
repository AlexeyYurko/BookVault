from sqlalchemy import String
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.annotations import str_pk
from app.db.base import Base
from app.models import Book


class Language(Base):
    __tablename__ = 'languages'

    code: Mapped[str_pk]
    name: Mapped[str] = mapped_column(String, nullable=False)

    books: Mapped[list["Book"]] = relationship(backref="language")