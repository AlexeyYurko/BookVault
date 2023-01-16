from fastapi import APIRouter, Request, File, Form, UploadFile
from sqlalchemy.orm import Session, joinedload
from starlette import status
from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates

from db.base import engine
from importers import DjvuImporter, EpubImporter, PdfImporter
from models import Book

ALLOWED_TYPES = {'application/pdf': PdfImporter, 'application/epub+zip': EpubImporter, 'application/djvu': DjvuImporter}

templates = Jinja2Templates(directory="templates")

router = APIRouter()


@router.post("/search", summary='Seed books', status_code=status.HTTP_200_OK)
def search_books(request: Request, query: str = Form(default='')):
    with Session(bind=engine) as session:
        books = session.query(Book).options(joinedload(Book.tags)).filter(Book.title.ilike(f"%{query}%")).all()
    tags = []
    for book in books:
        tags.extend(iter(book.tags))
    return templates.TemplateResponse('books_list.html', {'request': request, 'books': books, 'tags': set(tags)})


@router.get('/add_books')
def show_add_books_view(request: Request):
    return templates.TemplateResponse('add_books.html', {'request': request})


@router.post('/add_books')
def add_books(request: Request, file: UploadFile = File(), tags: str = Form(default='')):
    tags = tags.lower().split(',')
    file_type = file.content_type
    if file_type not in ALLOWED_TYPES:
        return templates.TemplateResponse('add_books.html', {'request': request, 'error': 'Invalid file type'})
    tags = {tag.strip() for tag in tags}
    book_importer = ALLOWED_TYPES[file_type](file, tags)
    book_importer.process()
    return RedirectResponse(request.url_for("homepage"), status_code=303)


@router.get('/{book_id}')
def show_book(request: Request, book_id: int):
    with Session(bind=engine) as session:
        book = session.query(Book).options(joinedload(Book.tags)).filter(Book.id == book_id).first()
        return templates.TemplateResponse('book_view.html', {'request':request, 'book': book, 'tags': book.tags})
