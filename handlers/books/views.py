from typing import List

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Request,
    UploadFile,
)
from starlette import status
from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates

from handlers.books.dependencies import (
    get_book_by_id,
    get_book_by_tag,
    get_searched_books,
)
from importers import (
    DjvuImporter,
    EpubImporter,
    PdfImporter,
)

ALLOWED_TYPES = {'application/pdf': PdfImporter, 'application/epub+zip': EpubImporter, 'application/djvu': DjvuImporter}

templates = Jinja2Templates(directory="templates")

router = APIRouter()


@router.post("/search", summary='Search books', status_code=status.HTTP_200_OK)
def search_books(request: Request, books=Depends(get_searched_books)):
    tags = []
    for book in books:
        tags.extend(iter(book.tags))
    return templates.TemplateResponse('books_list.html', {'request': request, 'books': books, 'tags': set(tags)})


@router.get('/add_books')
def show_add_books_view(request: Request):
    return templates.TemplateResponse('add_books.html', {'request': request})


@router.post('/add_books')
def add_books(request: Request, files: List[UploadFile] = File(), tags: str = Form(default='')):
    tags = tags.lower().split(',')
    for file in files:
        file_type = file.content_type
        if file_type not in ALLOWED_TYPES:
            continue
        tags = {tag.strip() for tag in tags}
        book_importer = ALLOWED_TYPES[file_type](file, tags)
        book_importer.process()
    return RedirectResponse(request.url_for("homepage"), status_code=303)


@router.get('/{book_id}')
def show_book(request: Request, book=Depends(get_book_by_id)):
    return templates.TemplateResponse('book_view.html', {'request': request, 'book': book, 'tags': book.tags})


@router.get('/by_tag/{tag_name}')
def show_books_by_tag(request: Request, books=Depends(get_book_by_tag)):
    tags = []
    for book in books:
        tags.extend(iter(book.tags))
    return templates.TemplateResponse('books_list.html', {'request': request, 'books': books, 'tags': set(tags)})
