from flask import Blueprint, render_template
from sqlalchemy.orm import Session

from db import engine
from models import Book, Tag

home_bp = Blueprint('homepage', __name__, template_folder='templates')


@home_bp.route('/', methods=['GET'])
def homepage():
    with Session(bind=engine) as session:
        books = session.query(Book).all()
        tags = session.query(Tag).all()
    return render_template('index.html', books=books, tags=tags)






