from flask import Blueprint
from sqlalchemy.orm import Session

from base import Base, engine
from models import Book, Tag

datab = Blueprint('db', __name__, template_folder='templates')


@datab.route('/create_db', methods=['GET'])
def create_db():
    Base.metadata.create_all(engine)
    return {"message": "ok"}


@datab.route('/seed_db', methods=['GET'])
def seed_db():
    with Session(bind=engine) as session:
        first_tag = Tag(name="Fantasy")
        second_tag = Tag(name="Science Fiction")

        first_book = Book(title="The Lord of the Rings", author="J.R.R. Tolkien", isbn="0-395-19395-8",
                          tags=[first_tag],)
        second_book = Book(title="The Hobbit", author="J.R.R. Tolkien", isbn="0-395-19395-8", tags=[first_tag],)
        third_book = Book(title="The Fellowship of the Ring", author="J.R.R. Tolkien", isbn="0-395-19395-8",
                          tags=[first_tag],)
        fourth_book = Book(title="Foundation", author="Isaac Asimov", isbn="0-395-19395-8", tags=[second_tag],)
        session.add(first_book)
        session.add(second_book)
        session.add(third_book)
        session.add(fourth_book)
        session.commit()
    return {"message": "ok"}
