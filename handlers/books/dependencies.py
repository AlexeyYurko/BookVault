from typing import List

from fastapi import Depends, Form, HTTPException
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import joinedload, Query
from starlette import status

from db import Session, get_db_session
from models import Book


def get_books(db_session: Session = Depends(get_db_session)):
    return (
        db_session.query(Book)
        .options(joinedload(Book.tags))
    )


def get_searched_books(query: str = Form(default=''), books: Query = Depends(get_books)) -> List[Book]:
    return books.filter(Book.title.ilike(f"%{query}%")).all()


def get_book_by_id(book_id: int, books: Query = Depends(get_books)) -> Book | None:
    try:
        return books.filter(Book.id == book_id).one()
    except NoResultFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Book with id={book_id} not found')


def get_book_by_tag(tag_name: str, books: Query = Depends(get_books)) -> List[Book]:
    return books.filter(Book.tags.any(name=tag_name)).all()
