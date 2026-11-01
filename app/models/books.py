from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
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
    __table_args__ = (
        Index("ix_books_catalog_checksum", "catalog_id", "checksum"),
        Index("ix_books_publication_name", "publication_name"),
        Index("ix_books_issue_year", "issue_year"),
        CheckConstraint(
            "(issue_month IS NULL OR (issue_month >= 1 AND issue_month <= 12))",
            name="ck_books_issue_month_range",
        ),
    )

    id: Mapped[int_pk]
    title: Mapped[str] = mapped_column(String, nullable=False, index=True)
    isbn: Mapped[str] = mapped_column(String, nullable=True, index=True)
    original_isbn: Mapped[str] = mapped_column(String, nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=True)
    cover: Mapped[str] = mapped_column(String, nullable=True)
    amazon_url: Mapped[str] = mapped_column(String, nullable=True)
    goodreads_url: Mapped[str] = mapped_column(String, nullable=True)
    edition: Mapped[str] = mapped_column(String, nullable=True)
    publication_name: Mapped[str | None] = mapped_column(String, nullable=True)
    issue_number: Mapped[str | None] = mapped_column(String, nullable=True)
    issue_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    issue_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    issue_label: Mapped[str | None] = mapped_column(String, nullable=True)

    series_id: Mapped[int] = mapped_column(ForeignKey("book_series.id", name="book_series_fk"), nullable=True, index=True)
    series: Mapped["BookSeries | None"] = relationship(backref="books")

    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id", name="book_collections_fk"), nullable=True, index=True)
    collection: Mapped["Collection | None"] = relationship(backref="books")

    edition_group_id: Mapped[int] = mapped_column(ForeignKey("edition_groups.id", name="book_edition_group_fk"), nullable=True, index=True)
    edition_group: Mapped["EditionGroup | None"] = relationship(back_populates="books")

    catalog_id: Mapped[int] = mapped_column(ForeignKey("catalogs.id"), nullable=False, index=True)
    catalog: Mapped["Catalog"] = relationship(back_populates="books")

    checksum: Mapped[str] = mapped_column(String, nullable=True, index=True)
    format: Mapped[str] = mapped_column(String, nullable=True)

    manually_updated_fields: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    tags: Mapped[list["Tag"]] = relationship(secondary="books_tags", back_populates="books")
    authors: Mapped[list["Author"]] = relationship(secondary="books_authors", back_populates="books")  # noqa: F821

    publisher_id: Mapped[int] = mapped_column(ForeignKey("publishers.id", name="book_publishers_fk"), nullable=True, index=True)

    language_code: Mapped[str] = mapped_column(ForeignKey('languages.code'), nullable=False, index=True)

    file_path: Mapped[str | None] = mapped_column(String, nullable=True)

    reading_position: Mapped[str | None] = mapped_column(String, nullable=True)
    reading_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    reading_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f'[{self.id}] {self.title} - {self.authors}'


class Tag(Base):
    __tablename__ = 'tags'

    id: Mapped[int_pk]
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)

    books: Mapped[list["Book"]] = relationship(secondary="books_tags", back_populates="tags")

    def __repr__(self):
        return f'Tag(id={self.id}, name="{self.name}")'


from app.models.catalog import Catalog  # noqa: E402


class BookSeries(Base):
    __tablename__ = 'book_series'

    id: Mapped[int_pk]
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)


class Collection(Base):
    __tablename__ = 'collections'

    id: Mapped[int_pk]
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)


class EditionGroup(Base):
    __tablename__ = 'edition_groups'

    id: Mapped[int_pk]
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)

    books: Mapped[list["Book"]] = relationship(back_populates="edition_group")
