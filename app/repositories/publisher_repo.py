from sqlalchemy import func, select

from app.models import Publisher
from app.repositories.base import AbstractRepository


class PublisherRepository(AbstractRepository):
    def get_or_create(self, *, name: str) -> Publisher:
        publisher = self.session.scalars(
            select(Publisher).where(func.lower(Publisher.name) == name.lower()).order_by(Publisher.id).limit(1)
        ).first()
        if publisher is None:
            publisher = self.create(name=name)
            self.session.add(publisher)
            self.session.flush()
        return publisher
