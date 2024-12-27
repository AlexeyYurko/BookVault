from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.models import Book, Tag
from app.repositories.base import AbstractRepository


class BookRepository(AbstractRepository):
    def get_tags_linked_to_books(self):
        tags_query = (
            select(Tag)
            .join(Tag.books)
            .group_by(Tag.id)
            .having(func.count(Book.id) > 0)
            .order_by(Tag.name)
        )
        return self.session.scalars(tags_query).all()

    def get_searched_books(self, query: str) -> list[Book]:
        return (
            self.session
            .scalars(
                select(Book)
                .where(Book.title.ilike(f"%{query}%"))
            ).all()
        )

    def get_book_by_id(self, book_id: int) -> Book:
        book = (
            self.session
            .scalar(
                select(Book)
                .options(
                    joinedload(Book.tags)
                )
                .where(
                    Book.id == book_id)
            )
        )
        return book

    def get_books_by_tag(self, tag_name: str) -> list[Book]:
        return (
            self.session
            .scalars(
                select(Book)
                .where(Book.tags.any(name=tag_name))
            )
            .all())

    def get_all_books(self):
        return self.session.scalars(select(Book)).all()

    def add_tag(self, book: Book, tag: Tag) -> None:
        if tag not in book.tags:
            book.tags.append(tag)

    def remove_tag(self, book: Book, tag: Tag) -> None:
        if tag in book.tags:
            book.tags.remove(tag)

    def delete_books(self, book_ids: list[int]) -> None:
        self.session.query(Book).filter(Book.id.in_(book_ids)).delete(synchronize_session=False)
