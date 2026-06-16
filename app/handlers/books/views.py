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

from app.handlers.dependencies import get_data_store
from app.services.importers import DjvuImporter, EpubImporter, PdfImporter
from app.template_utils import templates

ALLOWED_TYPES = {
    'application/pdf': PdfImporter,
    'application/epub+zip': EpubImporter,
    'application/djvu': DjvuImporter,
}

router = APIRouter()


@router.post("/search", summary='Search books', status_code=status.HTTP_200_OK)
def search_books(request: Request, query: str = Form(default=''), store=Depends(get_data_store)):
    tags = []
    books = store.book_repo.get_searched_books(query)
    for book in books:
        tags.extend(iter(book.tags))
    tags = sorted(set(tags), key=lambda tag: tag.name)
    return templates.TemplateResponse('books_list.html', {'request': request, 'books': books, 'tags': tags})


@router.get('/add_books')
def show_add_books_view(request: Request):
    return templates.TemplateResponse('add_books.html', {'request': request})


@router.post('/add_books')
def add_books(request: Request, files: list[UploadFile] = File(), tags: str = Form(default=''), store=Depends(get_data_store)):
    tag_set = {tag.strip() for tag in tags.lower().split(',') if tag.strip()}
    for file in files:
        file_type = file.content_type
        if file_type not in ALLOWED_TYPES:
            continue
        book_importer = ALLOWED_TYPES[file_type](file, tag_set)
        with store.transaction():
            book_importer.process(store)
    return RedirectResponse(request.url_for("homepage"), status_code=status.HTTP_303_SEE_OTHER)


@router.get('/{book_id}')
def show_book(request: Request, book_id: int, store=Depends(get_data_store)):
    book = store.book_repo.get_book_by_id(book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Book with id={book_id} not found',
        )
    return templates.TemplateResponse('book_view.html', {'request': request, 'book': book, 'tags': book.tags})


@router.get('/by_tag/{tag_name}')
def show_books_by_tag(request: Request, tag_name: str, store=Depends(get_data_store)):
    books = store.book_repo.get_books_by_tag(tag_name)
    tags = []
    for book in books:
        tags.extend(iter(book.tags))
    tags = sorted(set(tags), key=lambda tag: tag.name)
    return templates.TemplateResponse('books_list.html', {'request': request, 'books': books, 'tags': tags})


@router.post("/books/{book_id}/tags")
def add_tag(request: Request, book_id: int, tag_name: str = Form(...), store=Depends(get_data_store)):
    with store.transaction():
        book = store.book_repo.get_book_by_id(book_id)
        if not book:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

        tag = store.tag_repo.get_or_create(name=tag_name)
        store.book_repo.add_tag(book, tag)

    return templates.TemplateResponse("tags.html", {"request": request, "book": book})


@router.delete("/books/{book_id}/tags/{tag_id}")
def remove_tag(request: Request, book_id: int, tag_id: int, store=Depends(get_data_store)):
    with store.transaction():
        book = store.book_repo.get_book_by_id(book_id)
        if not book:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

        tag = store.tag_repo.get_by_params(id=tag_id)
        if not tag:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

        store.book_repo.remove_tag(book, tag)

    return templates.TemplateResponse("tags.html", {"request": request, "book": book})


@router.post("/batch_action")
def batch_action(
    request: Request,
    action: str = Form(...),
    book_ids: list[int] = Form(...),
    tags: str = Form(default=''),
    store=Depends(get_data_store),
):
    if action == "delete":
        with store.transaction():
            store.book_repo.delete_books(book_ids)
    elif action == "update_tags":
        new_tags = [tag.strip().lower() for tag in tags.split(',') if tag.strip()]
        with store.transaction():
            for book_id in book_ids:
                book = store.book_repo.get_book_by_id(book_id)
                if book:
                    new_tag_objects = {store.tag_repo.get_or_create(name=tag_name) for tag_name in new_tags}
                    existing_tags = set(book.tags)
                    merged_tags = existing_tags.union(new_tag_objects)
                    book.tags = list(merged_tags)

    return RedirectResponse(request.url_for("homepage"), status_code=status.HTTP_303_SEE_OTHER)
