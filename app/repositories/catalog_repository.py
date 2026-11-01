from sqlalchemy import func, select

from app.models import Book
from app.repositories.base import AbstractRepository


class CatalogRepository(AbstractRepository):
    def count_books(self, catalog_id: int) -> int:
        return self.session.scalar(select(func.count(Book.id)).where(Book.catalog_id == catalog_id)) or 0
