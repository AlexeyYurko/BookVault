from .base import Session


def get_db_session():
    with Session() as session:
        yield session