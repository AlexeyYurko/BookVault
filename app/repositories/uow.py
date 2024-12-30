from contextlib import contextmanager

from app.db import Session
from app.models import Book, Tag
from app.models.author import Author
from app.models.publishers import Publisher
from app.repositories.author_repo import AuthorRepository
from app.repositories.book_repository import BookRepository
from app.repositories.publisher_repo import PublisherRepository
from app.repositories.tag_repository import TagRepository


class UnitOfWork:
    def __init__(self, session):
        self._session = session
        self.book_repo = BookRepository(session, Book)
        self.tag_repo = TagRepository(session, Tag)
        self.author_repo = AuthorRepository(session, Author)
        self.publisher_repo = PublisherRepository(session, Publisher)

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
