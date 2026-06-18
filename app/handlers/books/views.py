import subprocess
from pathlib import Path

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from starlette import status
from starlette.responses import RedirectResponse

from app.handlers.dependencies import DataStoreDependency
from app.services.importers import DjvuImporter, EpubImporter, PdfImporter
from app.template_utils import templates

ALLOWED_TYPES = {
    "application/pdf": PdfImporter,
    "application/epub+zip": EpubImporter,
    "application/djvu": DjvuImporter,
}

router = APIRouter()


@router.post("/search", summary="Search books", status_code=status.HTTP_200_OK)
def search_books(
    request: Request,
    store: DataStoreDependency,
    query: str = Form(default=""),
):
    tags = []
    books = store.book_repo.get_searched_books(query)
    for book in books:
        tags.extend(iter(book.tags))
    tags = sorted(set(tags), key=lambda tag: tag.name)
    return templates.TemplateResponse("books_list.html", {"request": request, "books": books, "tags": tags})


@router.get("/add_books")
def show_add_books_view(request: Request):
    return templates.TemplateResponse("add_books.html", {"request": request})


@router.post("/add_books")
def add_books(
    request: Request,
    store: DataStoreDependency,
    files: list[UploadFile] = File(),
    tags: str = Form(default=""),
):
    tag_set = {tag.strip() for tag in tags.lower().split(",") if tag.strip()}
    for file in files:
        file_type = file.content_type
        if file_type not in ALLOWED_TYPES:
            continue
        book_importer = ALLOWED_TYPES[file_type](file, tag_set)
        with store.transaction():
            book_importer.process(store)
    return RedirectResponse(request.url_for("homepage"), status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{book_id}")
def show_book(
    request: Request,
    book_id: int,
    store: DataStoreDependency,
):
    book = store.book_repo.get_book_by_id(book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id={book_id} not found",
        )
    return templates.TemplateResponse("book_view.html", {"request": request, "book": book, "tags": book.tags})


@router.get("/{book_id}/download")
def download_book(
    request: Request,
    book_id: int,
    store: DataStoreDependency,
):
    book = store.book_repo.get_book_by_id(book_id)
    if not book or not book.file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    file_path = Path(book.file_path)
    if not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")

    # only works when server is on local machine (server and browser share filesystem)
    subprocess.Popen(["open", str(file_path)])
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/by_tag/{tag_name}")
def show_books_by_tag(
    request: Request,
    tag_name: str,
    store: DataStoreDependency,
):
    books = store.book_repo.get_books_by_tag(tag_name)
    tags = []
    for book in books:
        tags.extend(iter(book.tags))
    tags = sorted(set(tags), key=lambda tag: tag.name)
    return templates.TemplateResponse("books_list.html", {"request": request, "books": books, "tags": tags})


@router.post("/books/{book_id}/tags")
def add_tag(
    request: Request,
    book_id: int,
    store: DataStoreDependency,
    tag_name: str = Form(...),
):
    with store.transaction():
        book = store.book_repo.get_book_by_id(book_id)
        if not book:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

        tag = store.tag_repo.get_or_create(name=tag_name)
        store.book_repo.add_tag(book, tag)

    return templates.TemplateResponse("tags.html", {"request": request, "book": book})


@router.delete("/books/{book_id}/tags/{tag_id}")
def remove_tag(
    request: Request,
    book_id: int,
    tag_id: int,
    store: DataStoreDependency,
):
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
    store: DataStoreDependency,
    action: str = Form(...),
    book_ids: list[int] = Form(...),
    tags: str = Form(default=""),
):
    if action == "delete":
        with store.transaction():
            store.book_repo.delete_books(book_ids)
    elif action == "update_tags":
        new_tags = [tag.strip().lower() for tag in tags.split(",") if tag.strip()]
        with store.transaction():
            for book_id in book_ids:
                book = store.book_repo.get_book_by_id(book_id)
                if book:
                    new_tag_objects = {store.tag_repo.get_or_create(name=tag_name) for tag_name in new_tags}
                    existing_tags = set(book.tags)
                    merged_tags = existing_tags.union(new_tag_objects)
                    book.tags = list(merged_tags)

    return RedirectResponse(request.url_for("homepage"), status_code=status.HTTP_303_SEE_OTHER)
