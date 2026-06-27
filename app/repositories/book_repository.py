from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload

from app.models import Book, BookSeries, Collection, Tag
from app.models.author import Author
from app.models.publishers import Publisher
from app.repositories.base import AbstractRepository

SORTABLE_COLUMNS = frozenset({"title", "added_at", "edition", "publisher_id", "language_code"})
DEFAULT_SORT_BY = "title"
DEFAULT_SORT_ORDER = "asc"


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


class BookRepository(AbstractRepository):
    def get_tags_linked_to_books(self):
        tags_query = select(Tag).join(Tag.books).group_by(Tag.id).having(func.count(Book.id) > 0).order_by(Tag.name)
        return self.session.scalars(tags_query).all()

    def get_searched_books(
        self,
        query: str,
        page: int = 1,
        per_page: int = 20,
        sort_by: str = DEFAULT_SORT_BY,
        order: str = DEFAULT_SORT_ORDER,
    ) -> tuple[list[Book], int, int]:
        pattern = f"%{query}%"
        where = or_(
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
        total = self.session.scalar(select(func.count()).select_from(Book).where(where)) or 0
        page = max(1, min(page, _total_pages(total, per_page)))
        primary, tiebreaker = _order_clause(sort_by, order)
        books = self.session.scalars(
            select(Book).where(where).order_by(primary, tiebreaker).offset((page - 1) * per_page).limit(per_page)
        ).all()
        return books, total, page

    def get_book_by_id(self, book_id: int) -> Book:
        book = self.session.scalar(select(Book).options(joinedload(Book.tags)).where(Book.id == book_id))
        return book

    def get_books_by_tag(
        self,
        tag_name: str,
        page: int = 1,
        per_page: int = 20,
        sort_by: str = DEFAULT_SORT_BY,
        order: str = DEFAULT_SORT_ORDER,
    ) -> tuple[list[Book], int, int]:
        where = Book.tags.any(name=tag_name)
        total = self.session.scalar(select(func.count()).select_from(Book).where(where)) or 0
        page = max(1, min(page, _total_pages(total, per_page)))
        primary, tiebreaker = _order_clause(sort_by, order)
        books = self.session.scalars(
            select(Book).where(where).order_by(primary, tiebreaker).offset((page - 1) * per_page).limit(per_page)
        ).all()
        return books, total, page

    def get_all_books(
        self,
        page: int = 1,
        per_page: int = 20,
        sort_by: str = DEFAULT_SORT_BY,
        order: str = DEFAULT_SORT_ORDER,
    ) -> tuple[list[Book], int, int]:
        total = self.session.scalar(select(func.count()).select_from(Book)) or 0
        page = max(1, min(page, _total_pages(total, per_page)))
        primary, tiebreaker = _order_clause(sort_by, order)
        books = self.session.scalars(
            select(Book).order_by(primary, tiebreaker).offset((page - 1) * per_page).limit(per_page)
        ).all()
        return books, total, page

    def add_tag(self, book: Book, tag: Tag) -> None:
        if tag not in book.tags:
            book.tags.append(tag)

    def remove_tag(self, book: Book, tag: Tag) -> None:
        if tag in book.tags:
            book.tags.remove(tag)

    def delete_books(self, book_ids: list[int]) -> None:
        self.session.query(Book).filter(Book.id.in_(book_ids)).delete(synchronize_session=False)
        self.session.expire_all()
