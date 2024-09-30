from fastapi import (
    Depends,
    Form,
    HTTPException,
)
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from starlette import status

from db import (
    Session,
    get_db_session,
)
from models import Book


def get_searched_books(query: str = Form(default=''), db_session: Session = Depends(get_db_session)) -> list[Book]:
    return db_session.scalars(select(Book).where(Book.title.ilike(f"%{query}%"))).all()


def get_book_by_id(book_id: int, db_session: Session = Depends(get_db_session)) -> Book:
    book = db_session.scalar(select(Book).options(joinedload(Book.tags)).where(Book.id == book_id))
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Book with id={book_id} not found',
        )
    return book


def get_book_by_tag(tag_name: str, db_session: Session = Depends(get_db_session)) -> list[Book]:
    return db_session.scalars(select(Book).where(Book.tags.any(name=tag_name))).all()
