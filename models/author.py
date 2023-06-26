from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from db.base import Base


class Author(Base):
    __tablename__ = 'authors'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    books = relationship("Book", secondary="books_authors", back_populates="authors", lazy='joined')

    def __repr__(self):
        return f'{self.name}'
