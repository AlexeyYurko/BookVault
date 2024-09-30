from sqlalchemy import String
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from db.annotations import int_pk
from db.base import Base
from models import Book


class Author(Base):
    __tablename__ = 'authors'

    id: Mapped[int_pk]
    name: Mapped[str] = mapped_column(String, nullable=False)

    books: Mapped[list[Book]] = relationship(secondary="books_authors", back_populates="authors", lazy='joined')


    def __repr__(self):
        return f'{self.name}'
