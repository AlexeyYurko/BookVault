from sqlalchemy import func, select

from app.models import Tag
from app.repositories.base import AbstractRepository


class TagRepository(AbstractRepository):
    def get_or_create(self, *, name: str) -> Tag:
        tag = self.session.scalars(
            select(Tag).where(func.lower(Tag.name) == name.lower()).order_by(Tag.id).limit(1)
        ).first()
        if tag is None:
            tag = self.create(name=name)
            self.session.add(tag)
            self.session.flush()
        return tag
