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

from app.handlers.dependencies import (
    get_uow,
)
from app.services.importers import (
    DjvuImporter,
    EpubImporter,
    PdfImporter,
)

ALLOWED_TYPES = {
    'application/pdf': PdfImporter,
    'application/epub+zip': EpubImporter,
    'application/djvu': DjvuImporter,
}

templates = Jinja2Templates(directory="templates")

router = APIRouter()


@router.post("/search", summary='Search books', status_code=status.HTTP_200_OK)
def search_books(request: Request, query: str = Form(default=''), uow=Depends(get_uow)):
    tags = []
    books = uow.book_repo.get_searched_books(query)
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
def show_book(request: Request, book_id: int, uow=Depends(get_uow)):
    book = uow.book_repo.get_book_by_id(book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Book with id={book_id} not found',
        )
    return templates.TemplateResponse('book_view.html', {'request': request, 'book': book, 'tags': book.tags})


@router.get('/by_tag/{tag_name}')
def show_books_by_tag(request: Request, tag_name: str, uow=Depends(get_uow)):
    books = uow.book_repo.get_books_by_tag(tag_name)
    tags = []
    for book in books:
        tags.extend(iter(book.tags))
    return templates.TemplateResponse('books_list.html', {'request': request, 'books': books, 'tags': set(tags)})


@router.post("/books/{book_id}/tags")
def add_tag(request: Request, book_id: int, tag_name: str = Form(...), uow=Depends(get_uow)):
    with uow.transaction():
        book = uow.book_repo.get_book_by_id(book_id)
        if not book:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

        tag = uow.tag_repo.get_or_create(name=tag_name)
        uow.book_repo.add_tag(book, tag)

    return templates.TemplateResponse("tags.html", {"request": request, "book": book})


@router.delete("/books/{book_id}/tags/{tag_id}")
def remove_tag(request: Request, book_id: int, tag_id: int, uow=Depends(get_uow)):
    with uow.transaction():
        book = uow.book_repo.get_book_by_id(book_id)
        if not book:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

        tag = uow.tag_repo.get_by_params(id=tag_id)
        if not tag:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

        uow.book_repo.remove_tag(book, tag)

    return templates.TemplateResponse("tags.html", {"request": request, "book": book})


@router.post("/batch_action")
def batch_action(
        request: Request,
        action: str = Form(...),
        book_ids: list[int] = Form(...),
        tags: str = Form(default=''),
        uow=Depends(get_uow),
):
    if action == "delete":
        with uow.transaction():
            uow.book_repo.delete_books(book_ids)
    elif action == "update_tags":
        new_tags = [tag.strip().lower() for tag in tags.split(',') if tag.strip()]
        with uow.transaction():
            for book_id in book_ids:
                book = uow.book_repo.get_book_by_id(book_id)
                if book:
                    book.tags = [uow.tag_repo.get_or_create(name=tag_name) for tag_name in new_tags]

    return RedirectResponse(request.url_for("homepage"), status_code=status.HTTP_303_SEE_OTHER)
