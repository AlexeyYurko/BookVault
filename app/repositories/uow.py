from contextlib import contextmanager

from app.db import Session
from app.models import Book, Tag
from app.repositories.book_repository import BookRepository
from app.repositories.tag_repository import TagRepository


class UnitOfWork:
    def __init__(self, session):
        self._session = session
        self.book_repo = BookRepository(session, Book)
        self.tag_repo = TagRepository(session, Tag)

    @contextmanager
    def transaction(self):
        try:
            yield self
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

    @property
    def session(self) -> Session:
        return self._session
