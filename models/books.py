from sqlalchemy import Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import relationship

from db.base import Base

books_tags = Table('books_tags', Base.metadata,
                   Column('book_id', ForeignKey('books.id'), primary_key=True),
                   Column('tag_id', ForeignKey('tags.id'), primary_key=True)
                   )

books_authors = Table('books_authors', Base.metadata,
                      Column('book_id', ForeignKey('books.id'), primary_key=True),
                      Column('author_id', ForeignKey('authors.id'), primary_key=True)
                      )


class Book(Base):
    __tablename__ = 'books'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    isbn = Column(String, nullable=True)
    description = Column(String, nullable=True)
    cover = Column(String, nullable=True)
    amazon_url = Column(String, nullable=True)
    goodreads_url = Column(String, nullable=True)
    checksum = Column(String, nullable=True)
    format = Column(String, nullable=False)
    tags = relationship("Tag", secondary="books_tags", back_populates='books')
    authors = relationship("Author", secondary="books_authors", back_populates='books', lazy='joined')


class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    books = relationship("Book", secondary="books_tags", back_populates="tags")
