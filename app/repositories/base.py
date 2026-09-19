from typing import TypeVar

from sqlalchemy import select

T = TypeVar('T')


class AbstractRepository[T]:
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

    def list_all(self, order_by_column: str | None = None) -> list[T]:
        query = select(self.model)
        if order_by_column is not None:
            query = query.order_by(getattr(self.model, order_by_column))
        return self.session.scalars(query).unique().all()
