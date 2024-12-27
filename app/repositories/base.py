from abc import ABC
from typing import Generic, TypeVar

from sqlalchemy import select

T = TypeVar('T')


class AbstractRepository(ABC, Generic[T]):
    def __init__(self, session, model):
        self.session = session
        self.model = model

    def create(self, **kwargs) -> T:
        entity = self.model(**kwargs)
        self.add(entity)
        return entity

    def get_by_params(self, **kwargs) -> T | None:
        query = select(self.model).filter_by(**kwargs)
        result = self.session.execute(query)
        return result.scalar_one_or_none()

    def add(self, entity):
        self.session.add(entity)
