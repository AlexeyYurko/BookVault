from fastapi import (
    APIRouter,
    Depends,
)
from sqlalchemy.orm import Session
from starlette import status

from db import get_db_session
from db.base import (
    Base,
    engine,
)
from models import (
    Book,
    BookSeries,
    Tag,
)
from models.author import Author
from models.language import Language
from models.publishers import Publisher

router = APIRouter()


@router.get("/seed_db", summary='Seed DB', status_code=status.HTTP_200_OK)
def seed_db(db_session: Session = Depends(get_db_session)):
    language = Language(code='en', name='English')

    lotr_series = BookSeries(name='Lord of the Rings')
    foundation_series = BookSeries(name='Foundation')

    first_tag = Tag(name="fantasy")
    second_tag = Tag(name="science fiction")

    first_author = Author(name='J.R.R. Tolkien')
    second_author = Author(name='Isaac Asimov')

    first_publisher = Publisher(name='Penguin Books')
    second_publisher = Publisher(name='Macmillan')

    first_book = Book(title="The Fellowship of the Ring", authors=[first_author], isbn="0-395-19395-8", format='pdf',
                      tags=[first_tag], publisher=first_publisher, language=language,
                      series=lotr_series)
    second_book = Book(title="The Hobbit", authors=[first_author], isbn="0-395-19395-8", format='epub',
                       tags=[first_tag], publisher=first_publisher, language=language,
                       series=lotr_series)
    third_book = Book(title="The Two Towers", authors=[first_author], isbn="0-395-19395-8",
                      format='epub', tags=[first_tag], publisher=first_publisher, language=language,
                      series=lotr_series)
    fourth_book = Book(title="Foundation", authors=[second_author], isbn="0-395-19395-8", format='epub',
                       tags=[second_tag], publisher=second_publisher, language=language, series=foundation_series)
    db_session.add(first_book)
    db_session.add(second_book)
    db_session.add(third_book)
    db_session.add(fourth_book)
    db_session.commit()
    return {"db_seed": "ok"}


@router.get("/create_db", summary='Create DB', status_code=status.HTTP_200_OK)
def create_db():
    Base.metadata.create_all(engine)
    return {"message": "ok"}
