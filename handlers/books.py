from flask import render_template, request
from sqlalchemy.orm import Session, joinedload

from db.database import engine
from models import Book


def search_books():
    query = request.form['query']
    with Session(bind=engine) as session:
        books = session.query(Book).options(joinedload(Book.tags)).filter(Book.title.ilike(f"%{query}%")).all()
    tags = []
    for book in books:
        tags.extend(iter(book.tags))
    return render_template('index.html', books=books, tags=set(tags))
