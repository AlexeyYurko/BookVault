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
        return result.unique().scalar_one_or_none()

    def add(self, entity):
        self.session.add(entity)

    def get_or_create(self, **kwargs) -> T | None:
        obj = self.get_by_params(**kwargs)
        if not obj:
            obj = self.create(**kwargs)
            self.session.add(obj)
            self.session.flush()
        return obj
