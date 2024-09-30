from fastapi import Depends
from sqlalchemy import (
    func,
    select,
)

from db import (
    Session,
    get_db_session,
)
from models import (
    Book,
    Tag,
)


def get_all_books(db_session: Session = Depends(get_db_session)):
    return db_session.scalars(select(Book)).all()


def get_tags_linked_to_books(db_session: Session = Depends(get_db_session)):
    tags_query = (
        select(Tag)
        .join(Tag.books)
        .group_by(Tag.id)
        .having(func.count(Book.id) > 0)
        .order_by(Tag.name)
    )
    return db_session.scalars(tags_query).all()
