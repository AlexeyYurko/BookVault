from typing import List

from sqlalchemy import  String
from sqlalchemy.orm import relationship, Mapped, mapped_column

from db.annotations import str_pk
from db.base import Base
from models import Book


class Language(Base):
    __tablename__ = 'languages'

    code: Mapped[str_pk]
    name: Mapped[str] = mapped_column(String, nullable=False)

    books: Mapped[List["Book"]] = relationship(backref="language")