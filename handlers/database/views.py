from fastapi import APIRouter
from sqlalchemy.orm import Session
from starlette import status

from db.base import Base, engine
from models import Book, Tag
from models.author import Author
from models.publishers import Publisher

router = APIRouter()


@router.get("/seed_db", summary='Seed DB', status_code=status.HTTP_200_OK)
def seed_db():
    with Session(bind=engine) as session:
        first_tag = Tag(name="Fantasy")
        second_tag = Tag(name="Science Fiction")

        first_author = Author(name='J.R.R. Tolkien')
        second_author = Author(name='Isaac Asimov')

        first_publisher = Publisher(name='Penguin Books')
        second_publisher = Publisher(name='Macmillan')

        first_book = Book(title="The Lord of the Rings", authors=[first_author], isbn="0-395-19395-8", format='epub',
                          tags=[first_tag], publisher=first_publisher)
        second_book = Book(title="The Hobbit", authors=[first_author], isbn="0-395-19395-8", format='epub',
                           tags=[first_tag], publisher=first_publisher)
        third_book = Book(title="The Fellowship of the Ring", authors=[first_author], isbn="0-395-19395-8",
                          format='epub', tags=[first_tag], publisher=first_publisher)
        fourth_book = Book(title="Foundation", authors=[second_author], isbn="0-395-19395-8", format='epub',
                           tags=[second_tag], publisher=second_publisher)
        session.add(first_book)
        session.add(second_book)
        session.add(third_book)
        session.add(fourth_book)
        session.commit()
    return {"db_seed": "ok"}


@router.get("/create_db", summary='Create DB', status_code=status.HTTP_200_OK)
def create_db():
    Base.metadata.create_all(engine)
    return {"message": "ok"}
