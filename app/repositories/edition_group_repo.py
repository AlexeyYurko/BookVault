from sqlalchemy import select

from app.models import Book
from app.repositories.base import AbstractRepository

MIN_GROUP_SIZE = 2


class EditionGroupRepository(AbstractRepository):
    def books(self, group_id: int, exclude_book_id: int | None = None) -> list[Book]:
        stmt = select(Book).where(Book.edition_group_id == group_id)
        if exclude_book_id is not None:
            stmt = stmt.where(Book.id != exclude_book_id)
        return list(self.session.scalars(stmt.order_by(Book.language_code)).all())

    def prune(self, group_id: int | None) -> None:
        """Drop a group left with fewer than two books, ungrouping the rest."""
        if group_id is None:
            return
        group = self.get_by_params(id=group_id)
        if group is None:
            return
        books = self.books(group_id)
        if len(books) >= MIN_GROUP_SIZE:
            return
        for book in books:
            book.edition_group_id = None
        self.session.delete(group)
        self.session.flush()
