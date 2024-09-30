from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from starlette import status
from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates

from db import (
    Session,
    get_db_session,
)
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
from models import (
    Book,
    Tag,
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
def add_books(request: Request, files: list[UploadFile] = File(), tags: str = Form(default='')):
    tags = tags.lower().split(',')
    for file in files:
        file_type = file.content_type
        if file_type not in ALLOWED_TYPES:
            continue
        tags = {tag.strip() for tag in tags}
        book_importer = ALLOWED_TYPES[file_type](file, tags)
        book_importer.process()
    return RedirectResponse(request.url_for("homepage"), status_code=status.HTTP_303_SEE_OTHER)


@router.get('/{book_id}')
def show_book(request: Request, book=Depends(get_book_by_id)):
    return templates.TemplateResponse('book_view.html', {'request': request, 'book': book, 'tags': book.tags})


@router.get('/by_tag/{tag_name}')
def show_books_by_tag(request: Request, books=Depends(get_book_by_tag)):
    tags = []
    for book in books:
        tags.extend(iter(book.tags))
    return templates.TemplateResponse('books_list.html', {'request': request, 'books': books, 'tags': set(tags)})


@router.post("/books/{book_id}/tags")
def add_tag(request: Request, book_id: int, tag_name: str = Form(...), db_session: Session = Depends(get_db_session)):
    book = db_session.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    tag = Tag.get_or_create(db_session, tag_name)
    book.add_tag(tag)
    db_session.commit()

    return templates.TemplateResponse("tags.html", {"request": request, "book": book})


@router.delete("/books/{book_id}/tags/{tag_id}")
def remove_tag(request: Request, book_id: int, tag_id: int, db_session: Session = Depends(get_db_session)):
    book = db_session.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    tag = db_session.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    book.remove_tag(tag)
    db_session.commit()

    return templates.TemplateResponse("tags.html", {"request": request, "book": book})


@router.post("/batch_action")
def batch_action(
        request: Request,
        action: str = Form(...),
        book_ids: list[int] = Form(...),
        tags: str = Form(default=''),
        db_session: Session = Depends(get_db_session)
):
    if action == "delete":
        db_session.query(Book).filter(Book.id.in_(book_ids)).delete(synchronize_session=False)
    elif action == "update_tags":
        new_tags = [tag.strip().lower() for tag in tags.split(',') if tag.strip()]
        for book_id in book_ids:
            book = db_session.query(Book).get(book_id)
            if book:
                book.tags = [Tag.get_or_create(db_session, tag_name) for tag_name in new_tags]

    db_session.commit()
    return RedirectResponse(request.url_for("homepage"), status_code=status.HTTP_303_SEE_OTHER)
