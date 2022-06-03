from sqlalchemy import Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import relationship

from db.database import Base

books_tags = Table('books_tags', Base.metadata,
                   Column('book_id', ForeignKey('books.id'), primary_key=True),
                   Column('tag_id', ForeignKey('tags.id'), primary_key=True)
                   )


class Book(Base):
    __tablename__ = 'books'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=True)
    isbn = Column(String, nullable=True)
    description = Column(String, nullable=True)
    cover = Column(String, nullable=True)
    amazon_url = Column(String, nullable=True)
    goodreads_url = Column(String, nullable=True)
    checksum = Column(String, nullable=True)
    tags = relationship("Tag", secondary="books_tags", back_populates='books')


class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    books = relationship("Book", secondary="books_tags", back_populates="tags")
