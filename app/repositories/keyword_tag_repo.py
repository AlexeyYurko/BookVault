from sqlalchemy import select

from app.repositories.base import AbstractRepository


class KeywordTagRepository(AbstractRepository):
    def get_all_keywords(self) -> list[str]:
        rows = self.session.scalars(select(self.model).order_by(self.model.keyword)).all()
        return [row.keyword for row in rows]
