from sqlalchemy import String
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.annotations import int_pk
from app.db.base import Base


class Publisher(Base):
    __tablename__ = 'publishers'

    id: Mapped[int_pk]
    name: Mapped[str] = mapped_column(String, nullable=False)

    books: Mapped[list["Book"]] = relationship(backref="publisher")