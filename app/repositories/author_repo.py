from sqlalchemy import func, select

from app.models import Author
from app.repositories.base import AbstractRepository


class AuthorRepository(AbstractRepository):
    def get_or_create(self, *, name: str) -> Author:
        author = self.session.scalars(
            select(Author).where(func.lower(Author.name) == name.lower()).order_by(Author.id).limit(1)
        ).first()
        if author is None:
            author = self.create(name=name)
            self.session.add(author)
            self.session.flush()
        return author
