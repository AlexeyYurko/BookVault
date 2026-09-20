import subprocess
from pathlib import Path

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from sqlalchemy import select
from starlette import status
from starlette.responses import RedirectResponse

from app.handlers.dependencies import DataStoreDependency
from app.models import Book
from app.models.books import BookSeries
from app.models.language import Language
from app.services.importers import DjvuImporter, EpubImporter, PdfImporter
from app.services.importers.dedup_guard import release, try_claim
from app.services.metadata_resync import (
    FIELD_LABELS,
    mark_fields_updated,
    reset_field_protection,
    resync_book_metadata,
)
from app.template_utils import (
    DEFAULT_PER_PAGE,
    Pagination,
    build_filter_context,
    extract_filters,
    normalize_pagination,
    normalize_sort,
    templates,
)

ALLOWED_TYPES = {
    "application/pdf": PdfImporter,
    "application/epub+zip": EpubImporter,
    "application/djvu": DjvuImporter,
}

RESYNC_NOTICES = {
    "ok": ("Metadata re-synced from file.", True),
    "no_file": ("No file path stored for this book.", False),
    "missing_file": ("File not found on disk.", False),
    "unsupported": ("Unsupported file format for resync.", False),
    "failed": ("Failed to re-read metadata from the file.", False),
    "unprotected": ("Field protection cleared.", True),
}

router = APIRouter()


@router.get("/search", summary="Search books", status_code=status.HTTP_200_OK)
def search_books(  # noqa: PLR0913
    request: Request,
    store: DataStoreDependency,
    query: str = Query(default=""),
    page: int | None = None,
    per_page: int | None = None,
    sort_by: str | None = None,
    order: str | None = None,
):
    page, per_page_size = normalize_pagination(page, per_page)
    sort_by, sort_order = normalize_sort(sort_by, order)
    filters = extract_filters(request.query_params)
    books, total, page = store.book_repo.get_searched_books(
        query, page=page, per_page=per_page_size, sort_by=sort_by, order=sort_order, filters=filters
    )
    tags = []
    for book in books:
        tags.extend(iter(book.tags))
    tags = sorted(set(tags), key=lambda tag: tag.name)
    extra_query = {"query": query} if query else {}
    extra_query.update(filters)
    pagination = Pagination(
        request=request,
        route_name="search_books",
        page=page,
        per_page=per_page_size,
        total=total,
        sort_by=sort_by,
        sort_order=sort_order,
        extra_query=extra_query or None,
    )
    filter_context = build_filter_context(store)
    template = "books_list.html" if request.headers.get("hx-request") == "true" else "index.html"
    return templates.TemplateResponse(
        template,
        {
            "request": request,
            "books": books,
            "tags": tags,
            "pagination": pagination,
            "per_page": per_page_size,
            "default_per_page": DEFAULT_PER_PAGE,
            "active_filters": filters,
            **filter_context,
        },
    )


@router.get("/filter")
def filter_books(  # noqa: PLR0913
    request: Request,
    store: DataStoreDependency,
    tags: str = Query(default=""),
    page: int | None = None,
    per_page: int | None = None,
    sort_by: str | None = None,
    order: str | None = None,
):
    tag_names = [tag.strip().lower() for tag in tags.split(",") if tag.strip()]
    page, per_page_size = normalize_pagination(page, per_page)
    sort_by, sort_order = normalize_sort(sort_by, order)
    filters = extract_filters(request.query_params)
    books, total, page = store.book_repo.get_books_by_tags(
        tag_names, page=page, per_page=per_page_size, sort_by=sort_by, order=sort_order, filters=filters
    )
    related_tags = store.book_repo.get_related_tags(tag_names)
    extra_query = {"tags": tags}
    extra_query.update(filters)
    pagination = Pagination(
        request=request,
        route_name="filter_books",
        page=page,
        per_page=per_page_size,
        total=total,
        sort_by=sort_by,
        sort_order=sort_order,
        extra_query=extra_query,
    )
    filter_context = build_filter_context(store)
    template = "books_list.html" if request.headers.get("hx-request") == "true" else "index.html"
    return templates.TemplateResponse(
        template,
        {
            "request": request,
            "books": books,
            "tags": related_tags,
            "active_tags": tag_names,
            "pagination": pagination,
            "per_page": per_page_size,
            "default_per_page": DEFAULT_PER_PAGE,
            "active_filters": filters,
            **filter_context,
        },
    )


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
        if not try_claim(book_importer.checksum):
            continue
        try:
            with store.transaction():
                book_importer.process(store)
        finally:
            release(book_importer.checksum)
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


@router.get("/{book_id}/detail")
def book_detail_panel(
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
    return templates.TemplateResponse("book_detail_panel.html", {"request": request, "book": book})


def _book_edit_values(book: Book, form: dict | None = None) -> dict:
    if form is not None:
        return {
            "title": form.get("title", ""),
            "authors": form.get("author_names", ""),
            "publisher": form.get("publisher_name", ""),
            "series": form.get("series_name", ""),
            "language_code": form.get("language_code", ""),
            "edition": form.get("edition", ""),
            "isbn": form.get("isbn", ""),
            "original_isbn": form.get("original_isbn", ""),
            "format": form.get("format", ""),
            "amazon_url": form.get("amazon_url", ""),
            "goodreads_url": form.get("goodreads_url", ""),
            "tags": form.get("tags_str", ""),
            "description": form.get("description", ""),
        }
    return {
        "title": book.title,
        "authors": ", ".join(author.name for author in book.authors),
        "publisher": book.publisher.name if book.publisher else "",
        "series": book.series.name if book.series else "",
        "language_code": book.language_code,
        "edition": book.edition or "",
        "isbn": book.isbn or "",
        "original_isbn": book.original_isbn or "",
        "format": book.format or "",
        "amazon_url": book.amazon_url or "",
        "goodreads_url": book.goodreads_url or "",
        "tags": ", ".join(tag.name for tag in book.tags),
        "description": book.description or "",
    }


def _edit_form_context(store) -> dict:
    return {
        "languages": store.book_repo.get_all_languages(),
        "authors": store.author_repo.list_all("name"),
        "publishers": store.publisher_repo.list_all("name"),
        "series_list": store.book_repo.get_all_series(),
        "formats": store.book_repo.get_formats_linked_to_books(),
    }


def _next_url(request: Request, url: str) -> str | None:
    if url and url.startswith(str(request.base_url)):
        return url
    return None


@router.get("/{book_id}/edit")
def edit_book(
    request: Request,
    book_id: int,
    store: DataStoreDependency,
):
    book = store.book_repo.get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Book with id={book_id} not found")

    resync_code = request.query_params.get("resync")
    notice = None
    if resync_code in RESYNC_NOTICES:
        message, is_ok = RESYNC_NOTICES[resync_code]
        notice = {"message": message, "is_ok": is_ok}

    return templates.TemplateResponse(
        "book_edit.html",
        {
            "request": request,
            "book": book,
            "values": _book_edit_values(book),
            "notice": notice,
            "protected_fields": [FIELD_LABELS[f] for f in (book.manually_updated_fields or []) if f in FIELD_LABELS],
            "next_url": _next_url(request, request.headers.get("referer", "")),
            **_edit_form_context(store),
        },
    )


@router.post("/{book_id}/resync")
def resync_metadata(
    request: Request,
    book_id: int,
    store: DataStoreDependency,
):
    book = store.book_repo.get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Book with id={book_id} not found")

    outcome = resync_book_metadata(store, book)
    url = request.url_for("edit_book", book_id=book_id).include_query_params(resync=outcome or "ok")
    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{book_id}/unprotect")
def unprotect_fields(
    request: Request,
    book_id: int,
    store: DataStoreDependency,
):
    book = store.book_repo.get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Book with id={book_id} not found")

    with store.transaction():
        reset_field_protection(book)

    url = request.url_for("edit_book", book_id=book_id).include_query_params(resync="unprotected")
    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)


def _edited_fields(book: Book, new: dict) -> list[str]:
    changed = []
    comparisons = [
        ("title", new.get("title"), book.title),
        ("description", new.get("description") or None, book.description),
        ("isbn", new.get("isbn") or None, book.isbn),
        ("original_isbn", new.get("original_isbn") or None, book.original_isbn),
        ("edition", new.get("edition") or None, book.edition),
        ("language", new.get("language_code"), book.language_code),
        ("authors", set(new.get("authors") or []), {author.name for author in book.authors}),
        ("publisher", new.get("publisher") or None, book.publisher.name if book.publisher else None),
        ("tags", set(new.get("tags") or []), {tag.name for tag in book.tags}),
        ("format", new.get("format") or None, book.format),
    ]
    for field, new_value, old_value in comparisons:
        if new_value != old_value:
            changed.append(field)
    return changed


@router.post("/{book_id}/edit")
def update_book(  # noqa: PLR0913
    request: Request,
    book_id: int,
    store: DataStoreDependency,
    title: str = Form(...),
    author_names: str = Form(default=""),
    publisher_name: str = Form(default=""),
    series_name: str = Form(default=""),
    language_code: str = Form(default=""),
    edition: str = Form(default=""),
    isbn: str = Form(default=""),
    original_isbn: str = Form(default=""),
    format: str = Form(default=""),
    amazon_url: str = Form(default=""),
    goodreads_url: str = Form(default=""),
    tags_str: str = Form(default=""),
    description: str = Form(default=""),
    next: str = Form(default=""),
):
    book = store.book_repo.get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Book with id={book_id} not found")

    title = title.strip()
    language_code = language_code.strip()
    language = store.session.get(Language, language_code)
    if not title or language is None:
        form = {
            "title": title,
            "author_names": author_names,
            "publisher_name": publisher_name,
            "series_name": series_name,
            "language_code": language_code,
            "edition": edition,
            "isbn": isbn,
            "original_isbn": original_isbn,
            "format": format,
            "amazon_url": amazon_url,
            "goodreads_url": goodreads_url,
            "tags_str": tags_str,
            "description": description,
        }
        return templates.TemplateResponse(
            "book_edit.html",
            {
                "request": request,
                "book": book,
                "values": _book_edit_values(book, form),
                "error": "Title and language are required.",
                "next_url": _next_url(request, next),
                **_edit_form_context(store),
            },
        )

    edited_fields = _edited_fields(
        book,
        {
            "title": title,
            "description": description.strip(),
            "isbn": isbn.strip(),
            "original_isbn": original_isbn.strip(),
            "edition": edition.strip(),
            "language_code": language_code,
            "authors": [name.strip() for name in author_names.split(",") if name.strip()],
            "publisher": publisher_name.strip(),
            "tags": [tag.strip().lower() for tag in tags_str.split(",") if tag.strip()],
            "format": format.strip(),
        },
    )

    with store.transaction():
        book.title = title
        book.isbn = isbn.strip() or None
        book.original_isbn = original_isbn.strip() or None
        book.edition = edition.strip() or None
        book.format = format.strip() or None
        book.amazon_url = amazon_url.strip() or None
        book.goodreads_url = goodreads_url.strip() or None
        book.description = description.strip() or None
        book.language = language

        authors = []
        seen_authors = set()
        for author_name in author_names.split(","):
            cleaned = author_name.strip()
            if not cleaned or cleaned.lower() in seen_authors:
                continue
            seen_authors.add(cleaned.lower())
            authors.append(store.author_repo.get_or_create(name=cleaned))
        book.authors = authors

        if publisher_name.strip():
            book.publisher = store.publisher_repo.get_or_create(name=publisher_name.strip())
        else:
            book.publisher = None

        if series_name.strip():
            series = store.session.scalar(select(BookSeries).where(BookSeries.name == series_name.strip()))
            if series is None:
                series = BookSeries(name=series_name.strip())
                store.session.add(series)
            book.series = series
        else:
            book.series = None

        tags = []
        for tag_name in tags_str.split(","):
            cleaned = tag_name.strip().lower()
            if not cleaned:
                continue
            tag = store.tag_repo.get_or_create(name=cleaned)
            if tag not in tags:
                tags.append(tag)
        book.tags = tags

        mark_fields_updated(book, edited_fields)

    target = _next_url(request, next) or request.url_for("show_book", book_id=book_id)
    return RedirectResponse(target, status_code=status.HTTP_303_SEE_OTHER)


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
def show_books_by_tag(  # noqa: PLR0913
    request: Request,
    tag_name: str,
    store: DataStoreDependency,
    page: int | None = None,
    per_page: int | None = None,
    sort_by: str | None = None,
    order: str | None = None,
):
    page, per_page_size = normalize_pagination(page, per_page)
    sort_by, sort_order = normalize_sort(sort_by, order)
    books, total, page = store.book_repo.get_books_by_tag(tag_name, page=page, per_page=per_page_size, sort_by=sort_by, order=sort_order)
    tags = []
    for book in books:
        tags.extend(iter(book.tags))
    tags = sorted(set(tags), key=lambda tag: tag.name)
    pagination = Pagination(
        request=request,
        route_name="show_books_by_tag",
        route_kwargs={"tag_name": tag_name},
        page=page,
        per_page=per_page_size,
        total=total,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return templates.TemplateResponse(
        "books_list.html",
        {
            "request": request,
            "books": books,
            "tags": tags,
            "pagination": pagination,
            "per_page": per_page_size,
            "default_per_page": DEFAULT_PER_PAGE,
        },
    )


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
        mark_fields_updated(book, ["tags"])

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
        mark_fields_updated(book, ["tags"])

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
                    mark_fields_updated(book, ["tags"])

    return RedirectResponse(request.url_for("homepage"), status_code=status.HTTP_303_SEE_OTHER)
