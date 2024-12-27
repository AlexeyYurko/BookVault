from app.models import Tag
from app.repositories.base import AbstractRepository


class TagRepository(AbstractRepository):
    def get_or_create(self, name: str) -> Tag:
        tag = self.get_by_params(name=name)
        if not tag:
            tag = self.create(name=name)
        return tag
