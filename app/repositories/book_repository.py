from dataclasses import dataclass

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import joinedload

from app.models import Book, BookSeries, Collection, Tag
from app.models.author import Author
from app.models.language import Language
from app.models.publishers import Publisher
from app.repositories.base import AbstractRepository

SORTABLE_COLUMNS = frozenset({"title", "added_at", "edition", "publisher_id", "language_code"})
DEFAULT_SORT_BY = "title"
DEFAULT_SORT_ORDER = "asc"


@dataclass(frozen=True)
class Page:
    books: list[Book]
    total: int
    page: int


def _total_pages(total: int, per_page: int) -> int:
    return max(1, (total + per_page - 1) // per_page) if total else 1


def _order_clause(sort_by: str, order: str):
    # whitelist via getattr prevents SQL injection: arbitrary column names
    # cannot reach the SQL. Invalid sort_by falls back to the default.
    column_name = sort_by if sort_by in SORTABLE_COLUMNS else DEFAULT_SORT_BY
    direction = "desc" if order.lower() == "desc" else "asc"
    column = getattr(Book, column_name)
    ordered = column.desc() if direction == "desc" else column.asc()
    # always tiebreak by id so paginated rows are stable across pages when the
    # sort column has many duplicate values (e.g. publisher_id=NULL).
    return ordered, Book.id.asc()


def _filter_conditions(filters: dict) -> list:
    conditions = []
    if filters.get("author"):
        conditions.append(Book.authors.any(Author.name == filters["author"]))
    if filters.get("language"):
        conditions.append(Book.language_code == filters["language"])
    if filters.get("publisher"):
        conditions.append(Book.publisher.has(Publisher.name == filters["publisher"]))
    if filters.get("series"):
        conditions.append(Book.series.has(BookSeries.name == filters["series"]))
    if filters.get("format"):
        conditions.append(Book.format == filters["format"])
    return conditions


class BookRepository(AbstractRepository):
    def get_tags_linked_to_books(self):
        tags_query = select(Tag).join(Tag.books).group_by(Tag.id).having(func.count(Book.id) > 0).order_by(Tag.name)
        return self.session.scalars(tags_query).unique().all()

    def get_authors_linked_to_books(self):
        query = select(Author).join(Author.books).group_by(Author.id).having(func.count(Book.id) > 0).order_by(Author.name)
        return self.session.scalars(query).unique().all()

    def get_languages_linked_to_books(self):
        query = select(Language).join(Language.books).group_by(Language.code).having(func.count(Book.id) > 0).order_by(Language.name)
        return self.session.scalars(query).unique().all()

    def get_publishers_linked_to_books(self):
        query = select(Publisher).join(Publisher.books).group_by(Publisher.id).having(func.count(Book.id) > 0).order_by(Publisher.name)
        return self.session.scalars(query).unique().all()

    def get_series_linked_to_books(self):
        query = select(BookSeries).join(BookSeries.books).group_by(BookSeries.id).having(func.count(Book.id) > 0).order_by(BookSeries.name)
        return self.session.scalars(query).unique().all()

    def get_formats_linked_to_books(self):
        query = select(Book.format).where(Book.format.isnot(None)).group_by(Book.format).order_by(Book.format)
        return [fmt for (fmt,) in self.session.execute(query).all()]

    def get_all_languages(self):
        return self.session.scalars(select(Language).order_by(Language.name)).all()

    def get_all_series(self):
        return self.session.scalars(select(BookSeries).order_by(BookSeries.name)).all()

    def find_books(  # noqa: PLR0913
        self,
        *,
        query: str | None = None,
        tags: list[str] | None = None,
        filters: dict | None = None,
        page: int = 1,
        per_page: int = 20,
        sort_by: str = DEFAULT_SORT_BY,
        order: str = DEFAULT_SORT_ORDER,
    ) -> Page:
        conditions: list = []
        if query:
            pattern = f"%{query}%"
            conditions.append(
                or_(
                    Book.title.ilike(pattern),
                    Book.isbn.ilike(pattern),
                    Book.description.ilike(pattern),
                    Book.edition.ilike(pattern),
                    Book.authors.any(Author.name.ilike(pattern)),
                    Book.tags.any(Tag.name.ilike(pattern)),
                    Book.publisher.has(Publisher.name.ilike(pattern)),
                    Book.series.has(BookSeries.name.ilike(pattern)),
                    Book.collection.has(Collection.name.ilike(pattern)),
                )
            )
        conditions.extend(Book.tags.any(name=name) for name in tags or ())
        conditions.extend(_filter_conditions(filters or {}))

        where = and_(*conditions) if conditions else None
        count_stmt = select(func.count()).select_from(Book)
        books_stmt = select(Book)
        if where is not None:
            count_stmt = count_stmt.where(where)
            books_stmt = books_stmt.where(where)

        total = self.session.scalar(count_stmt) or 0
        page = max(1, min(page, _total_pages(total, per_page)))
        primary, tiebreaker = _order_clause(sort_by, order)
        books = self.session.scalars(
            books_stmt.order_by(primary, tiebreaker).offset((page - 1) * per_page).limit(per_page)
        ).all()
        return Page(books=books, total=total, page=page)

    def get_book_by_id(self, book_id: int) -> Book:
        book = self.session.scalar(select(Book).options(joinedload(Book.tags)).where(Book.id == book_id))
        return book

    def get_related_tags(self, tag_names: list[str]) -> list[Tag]:
        stmt = select(Tag).join(Tag.books)
        if tag_names:
            stmt = stmt.where(and_(*(Book.tags.any(name=name) for name in tag_names)))
            stmt = stmt.where(Tag.name.notin_(tag_names))
        return self.session.scalars(stmt.group_by(Tag.id).having(func.count(Book.id) > 0).order_by(Tag.name)).unique().all()

    def add_tag(self, book: Book, tag: Tag) -> None:
        if tag not in book.tags:
            book.tags.append(tag)

    def remove_tag(self, book: Book, tag: Tag) -> None:
        if tag in book.tags:
            book.tags.remove(tag)

    def delete_books(self, book_ids: list[int]) -> None:
        self.session.query(Book).filter(Book.id.in_(book_ids)).delete(synchronize_session=False)
        self.session.expire_all()
