from flask import Blueprint, redirect, render_template, request, url_for
from sqlalchemy.orm import Session, joinedload

from db.database import engine
from importers import DjvuImporter, EpubImporter, PdfImporter
from models import Book

ALLOWED_TYPES = {'application/pdf': PdfImporter, 'application/epub+zip': EpubImporter, 'application/djvu': DjvuImporter}

books_bp = Blueprint('books', __name__, template_folder='templates')


@books_bp.route('/search', methods=['POST'])
def search_books():
    query = request.form['query']
    with Session(bind=engine) as session:
        books = session.query(Book).options(joinedload(Book.tags)).filter(Book.title.ilike(f"%{query}%")).all()
    tags = []
    for book in books:
        tags.extend(iter(book.tags))
    return render_template('index.html', books=books, tags=set(tags))


@books_bp.route('/add_books', methods=['POST', 'GET'])
def add_books():
    if request.method == 'GET':
        return render_template('add_books.html')
    file = request.files['file']
    file_type = file.content_type
    if file_type not in ALLOWED_TYPES:
        return render_template('add_books.html', error="Invalid file type")
    tags = [tag.strip() for tag in request.form['tags'].split(',')]
    book_importer = ALLOWED_TYPES[file_type](file, tags)
    book_importer.process()
    return redirect(url_for('homepage.homepage'))
