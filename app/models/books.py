from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    String,
    Table,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.annotations import int_pk
from app.db.base import Base

books_tags = Table('books_tags', Base.metadata,
                   Column('book_id', ForeignKey('books.id'), primary_key=True),
                   Column('tag_id', ForeignKey('tags.id'), primary_key=True)
                   )

books_authors = Table('books_authors', Base.metadata,
                      Column('book_id', ForeignKey('books.id'), primary_key=True),
                      Column('author_id', ForeignKey('authors.id'), primary_key=True)
                      )


class Book(Base):
    __tablename__ = 'books'

    id: Mapped[int_pk]
    title: Mapped[str] = mapped_column(String, nullable=False)
    isbn: Mapped[str] = mapped_column(String, nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=True)
    cover: Mapped[str] = mapped_column(String, nullable=True)
    amazon_url: Mapped[str] = mapped_column(String, nullable=True)
    goodreads_url: Mapped[str] = mapped_column(String, nullable=True)
    edition: Mapped[str] = mapped_column(String, nullable=True)

    series_id: Mapped[int] = mapped_column(ForeignKey("book_series.id", name="book_series_fk"), nullable=True)
    series: Mapped[list["BookSeries"]] = relationship(backref="books")

    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id", name="book_collections_fk"), nullable=True)
    collection: Mapped[list["Collection"]] = relationship(backref="books")

    checksum: Mapped[str] = mapped_column(String, nullable=True)
    format: Mapped[str] = mapped_column(String, nullable=True)

    tags: Mapped[list["Tag"]] = relationship(secondary="books_tags", back_populates="books")
    authors: Mapped[list["Author"]] = relationship(secondary="books_authors", back_populates="books")

    publisher_id: Mapped[int] = mapped_column(ForeignKey("publishers.id", name="book_publishers_fk"), nullable=True)

    language_code: Mapped[str] = mapped_column(ForeignKey('languages.code'), nullable=False)

    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f'[{self.id}] {self.title} - {self.authors}'


class Tag(Base):
    __tablename__ = 'tags'

    id: Mapped[int_pk]
    name: Mapped[str] = mapped_column(String, nullable=False)

    books: Mapped[list["Book"]] = relationship(secondary="books_tags", back_populates="tags")

    def __repr__(self):
        return f'Tag(id={self.id}, name="{self.name}")'


class BookSeries(Base):
    __tablename__ = 'book_series'

    id: Mapped[int_pk]
    name: Mapped[str] = mapped_column(String, nullable=False)


class Collection(Base):
    __tablename__ = 'collections'

    id: Mapped[int_pk]
    name: Mapped[str] = mapped_column(String, nullable=False)
