from flask import Blueprint
from sqlalchemy.orm import Session

from db.base import Base, engine
from models import Book, Tag
from models.author import Author

database_bp = Blueprint('db', __name__, template_folder='templates')


@database_bp.route('/create_db', methods=['GET'])
def create_db():
    Base.metadata.create_all(engine)
    return {"message": "ok"}


@database_bp.route('/seed_db', methods=['GET'])
def seed_db():
    with Session(bind=engine) as session:
        first_tag = Tag(name="Fantasy")
        second_tag = Tag(name="Science Fiction")

        first_author = Author(name='J.R.R. Tolkien')
        second_author = Author(name='Isaac Asimov')

        first_book = Book(title="The Lord of the Rings", authors=[first_author], isbn="0-395-19395-8", format='epub',
                          tags=[first_tag], )
        second_book = Book(title="The Hobbit", authors=[first_author], isbn="0-395-19395-8", format='epub',
                           tags=[first_tag], )
        third_book = Book(title="The Fellowship of the Ring", authors=[first_author], isbn="0-395-19395-8",
                          format='epub', tags=[first_tag], )
        fourth_book = Book(title="Foundation", authors=[second_author], isbn="0-395-19395-8", format='epub',
                           tags=[second_tag], )
        session.add(first_book)
        session.add(second_book)
        session.add(third_book)
        session.add(fourth_book)
        session.commit()
    return {"message": "ok"}
