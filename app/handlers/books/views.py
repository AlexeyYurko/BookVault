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
from fastapi.responses import FileResponse, RedirectResponse
from starlette import status

from app.config import settings
from app.handlers.dependencies import BookServiceDependency
from app.services.book_service import EditBookDTO, ImportedFile
from app.services.metadata_resync import FIELD_LABELS
from app.template_utils import (
    collect_book_tags,
    extract_filters,
    normalize_pagination,
    normalize_sort,
    render_book_list,
    templates,
)

RESYNC_NOTICES = {
    "ok": ("Metadata re-synced from file.", True),
    "no_file": ("No file path stored for this book.", False),
    "missing_file": ("File not found on disk.", False),
    "unsupported": ("Unsupported file format for resync.", False),
    "failed": ("Failed to re-read metadata from the file.", False),
    "unprotected": ("Field protection cleared.", True),
}

EDITION_NOTICES = {
    "linked": ("Book linked to another edition.", True),
    "unlinked": ("Book unlinked from its edition group.", True),
    "error": ("Could not link the selected book.", False),
}

router = APIRouter()


@router.get("/search", summary="Search books", status_code=status.HTTP_200_OK)
def search_books(  # noqa: PLR0913
    request: Request,
    book_service: BookServiceDependency,
    query: str = Query(default=""),
    page: int | None = None,
    per_page: int | None = None,
    sort_by: str | None = None,
    order: str | None = None,
):
    page, per_page_size = normalize_pagination(page, per_page)
    sort_by, sort_order = normalize_sort(sort_by, order)
    filters = extract_filters(request.query_params)
    books, total, page = book_service.search_books(
        query, page=page, per_page=per_page_size, sort_by=sort_by, order=sort_order, filters=filters
    )
    extra_query = {"query": query} if query else {}
    extra_query.update(filters)
    filter_context = book_service.filter_context()
    return render_book_list(
        request,
        context={
            "books": books,
            "tags": collect_book_tags(books),
            "edition_siblings": book_service.edition_siblings_map(books),
            "active_filters": filters,
            **filter_context,
        },
        route_name="search_books",
        page=page,
        per_page=per_page_size,
        total=total,
        sort_by=sort_by,
        sort_order=sort_order,
        extra_query=extra_query or None,
    )


@router.get("/filter")
def filter_books(  # noqa: PLR0913
    request: Request,
    book_service: BookServiceDependency,
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
    books, total, page = book_service.get_books_by_tags(
        tag_names, page=page, per_page=per_page_size, sort_by=sort_by, order=sort_order, filters=filters
    )
    related_tags = book_service.get_related_tags(tag_names)
    extra_query = {"tags": tags}
    extra_query.update(filters)
    filter_context = book_service.filter_context()
    return render_book_list(
        request,
        context={
            "books": books,
            "tags": related_tags,
            "active_tags": tag_names,
            "edition_siblings": book_service.edition_siblings_map(books),
            "active_filters": filters,
            **filter_context,
        },
        route_name="filter_books",
        page=page,
        per_page=per_page_size,
        total=total,
        sort_by=sort_by,
        sort_order=sort_order,
        extra_query=extra_query,
    )


@router.get("/add_books")
def show_add_books_view(request: Request):
    return templates.TemplateResponse("add_books.html", {"request": request})


@router.post("/add_books")
def add_books(
    request: Request,
    book_service: BookServiceDependency,
    files: list[UploadFile] = File(),
    tags: str = Form(default=""),
):
    imported = [ImportedFile(file=file.file, filename=file.filename, content_type=file.content_type) for file in files]
    book_service.import_files(imported, tags)
    return RedirectResponse(request.url_for("homepage"), status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{book_id}")
def show_book(
    request: Request,
    book_id: int,
    book_service: BookServiceDependency,
):
    book = book_service.get_book_by_id(book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id={book_id} not found",
        )
    next_param = request.query_params.get("next") or request.headers.get("referer", "")
    back_url = str(next_url(request, next_param) or request.url_for("homepage"))
    return templates.TemplateResponse(
        "book_view.html",
        {
            "request": request,
            "book": book,
            "tags": book.tags,
            "edition_siblings": book_service.edition_siblings(book),
            "back_url": back_url,
        },
    )


@router.get("/{book_id}/detail")
def book_detail_panel(
    request: Request,
    book_id: int,
    book_service: BookServiceDependency,
):
    book = book_service.get_book_by_id(book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id={book_id} not found",
        )
    return templates.TemplateResponse("book_detail_panel.html", {"request": request, "book": book})


def next_url(request: Request, url: str) -> str | None:
    if (
        url
        and url.startswith(str(request.base_url))
        and "/edit" not in url
        and "/lookup" not in url
    ):
        return url
    return None


@router.get("/{book_id}/edit")
def edit_book(
    request: Request,
    book_id: int,
    book_service: BookServiceDependency,
):
    book = book_service.get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Book with id={book_id} not found")

    resync_code = request.query_params.get("resync")
    edition_code = request.query_params.get("edition")
    notice = None
    if resync_code in RESYNC_NOTICES:
        message, is_ok = RESYNC_NOTICES[resync_code]
        notice = {"message": message, "is_ok": is_ok}
    elif edition_code in EDITION_NOTICES:
        message, is_ok = EDITION_NOTICES[edition_code]
        notice = {"message": message, "is_ok": is_ok}

    return templates.TemplateResponse(
        "book_edit.html",
        {
            "request": request,
            "book": book,
            "values": book_service.edit_values(book),
            "notice": notice,
            "edition_siblings": book_service.edition_siblings(book),
            "protected_fields": [FIELD_LABELS[f] for f in (book.manually_updated_fields or []) if f in FIELD_LABELS],
            "next_url": next_url(request, request.query_params.get("next") or request.headers.get("referer", "")),
            **book_service.edit_form_context(),
        },
    )


@router.post("/{book_id}/resync")
def resync_metadata(
    request: Request,
    book_id: int,
    book_service: BookServiceDependency,
):
    book = book_service.get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Book with id={book_id} not found")

    outcome = book_service.resync_metadata(book)
    url = request.url_for("edit_book", book_id=book_id).include_query_params(resync=outcome or "ok")
    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{book_id}/unprotect")
def unprotect_fields(
    request: Request,
    book_id: int,
    book_service: BookServiceDependency,
):
    book = book_service.get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Book with id={book_id} not found")

    book_service.unprotect_fields(book)

    url = request.url_for("edit_book", book_id=book_id).include_query_params(resync="unprotected")
    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{book_id}/lookup")
def lookup_metadata(
    request: Request,
    book_id: int,
    book_service: BookServiceDependency,
    query: str = Form(default=""),
    next: str = Form(default=""),
):
    book = book_service.get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Book with id={book_id} not found")

    result = book_service.lookup_values(book, query)

    return templates.TemplateResponse(
        "book_edit.html",
        {
            "request": request,
            "book": book,
            "values": result.values,
            "notice": result.notice,
            "error": result.error,
            "edition_siblings": book_service.edition_siblings(book),
            "protected_fields": [FIELD_LABELS[f] for f in (book.manually_updated_fields or []) if f in FIELD_LABELS],
            "next_url": next_url(request, next) or next_url(request, request.headers.get("referer", "")),
            **book_service.edit_form_context(),
        },
    )


@router.post("/{book_id}/edit")
def update_book(  # noqa: PLR0913
    request: Request,
    book_id: int,
    book_service: BookServiceDependency,
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
    book = book_service.get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Book with id={book_id} not found")

    dto = EditBookDTO(
        title=title.strip(),
        author_names=author_names,
        publisher_name=publisher_name,
        series_name=series_name,
        language_code=language_code.strip(),
        edition=edition,
        isbn=isbn,
        original_isbn=original_isbn,
        format=format,
        amazon_url=amazon_url,
        goodreads_url=goodreads_url,
        tags_str=tags_str,
        description=description,
    )
    validation = book_service.validate_edit(dto)

    if validation.errors:
        return templates.TemplateResponse(
            "book_edit.html",
            {
                "request": request,
                "book": book,
                "values": book_service.edit_values(book, dto),
                "error": " ".join(validation.errors),
                "next_url": next_url(request, next),
                **book_service.edit_form_context(),
            },
        )

    book_service.apply_edit(book, dto, validation)

    target = next_url(request, next) or request.url_for("show_book", book_id=book_id)
    return RedirectResponse(target, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{book_id}/editions/search")
def search_link_candidates(
    request: Request,
    book_id: int,
    book_service: BookServiceDependency,
    query: str = Query(default=""),
):
    book = book_service.get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Book with id={book_id} not found")

    candidates = book_service.find_link_candidates(book, query)
    return templates.TemplateResponse(
        "edition_link_results.html",
        {"request": request, "book": book, "candidates": candidates},
    )


@router.post("/{book_id}/editions/link")
def link_edition(
    request: Request,
    book_id: int,
    book_service: BookServiceDependency,
    target_book_id: int = Form(...),
):
    book = book_service.get_book_by_id(book_id)
    target = book_service.get_book_by_id(target_book_id)
    if not book or not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    try:
        book_service.link_edition(book, target)
        outcome = "linked"
    except ValueError:
        outcome = "error"

    url = request.url_for("edit_book", book_id=book_id).include_query_params(edition=outcome)
    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{book_id}/editions/unlink")
def unlink_edition(
    request: Request,
    book_id: int,
    book_service: BookServiceDependency,
):
    book = book_service.get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Book with id={book_id} not found")

    book_service.unlink_edition(book)

    url = request.url_for("edit_book", book_id=book_id).include_query_params(edition="unlinked")
    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{book_id}/download")
def download_book(
    request: Request,
    book_id: int,
    book_service: BookServiceDependency,
):
    book = book_service.get_book_by_id(book_id)
    if not book or not book.file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    file_path = Path(book.file_path)
    if not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")

    # Try to open locally (macOS), otherwise serve as file download
    try:
        import sys
        if sys.platform == "darwin":
            import subprocess as _subprocess
            _subprocess.Popen(["/usr/bin/open", str(file_path)])  # noqa: S603
            return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception:  # noqa: S110
        pass

    return FileResponse(
        str(file_path),
        media_type="application/octet-stream",
        filename=file_path.name,
        content_disposition_type="attachment",
    )


@router.get("/{book_id}/file")
def serve_book_file(
    request: Request,
    book_id: int,
    book_service: BookServiceDependency,
):
    book = book_service.get_book_by_id(book_id)
    if not book or not book.file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    file_path = Path(book.file_path)
    if not file_path.is_absolute():
        file_path = Path(settings.books_directory) / file_path if settings.books_directory else file_path

    if not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")

    if settings.books_directory:
        books_dir = Path(settings.books_directory).resolve()
        file_path_resolved = file_path.resolve()
        try:
            file_path_resolved.relative_to(books_dir)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied") from None

    return FileResponse(
        str(file_path),
        media_type="application/octet-stream",
        filename=file_path.name,
        content_disposition_type="inline",
    )


@router.get("/by_tag/{tag_name}")
def show_books_by_tag(  # noqa: PLR0913
    request: Request,
    tag_name: str,
    book_service: BookServiceDependency,
    page: int | None = None,
    per_page: int | None = None,
    sort_by: str | None = None,
    order: str | None = None,
):
    page, per_page_size = normalize_pagination(page, per_page)
    sort_by, sort_order = normalize_sort(sort_by, order)
    books, total, page = book_service.get_books_by_tag(
        tag_name, page=page, per_page=per_page_size, sort_by=sort_by, order=sort_order
    )
    return render_book_list(
        request,
        context={
            "books": books,
            "tags": collect_book_tags(books),
            "edition_siblings": book_service.edition_siblings_map(books),
        },
        route_name="show_books_by_tag",
        route_kwargs={"tag_name": tag_name},
        page=page,
        per_page=per_page_size,
        total=total,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post("/books/{book_id}/tags")
def add_tag(
    request: Request,
    book_id: int,
    book_service: BookServiceDependency,
    tag_name: str = Form(...),
):
    with book_service.transaction():
        book = book_service.get_book_by_id(book_id)
        if not book:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

        book_service.add_tag(book, tag_name)

    return templates.TemplateResponse("tags.html", {"request": request, "book": book})


@router.delete("/books/{book_id}/tags/{tag_id}")
def remove_tag(
    request: Request,
    book_id: int,
    tag_id: int,
    book_service: BookServiceDependency,
):
    with book_service.transaction():
        book = book_service.get_book_by_id(book_id)
        if not book:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

        if not book_service.remove_tag(book, tag_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    return templates.TemplateResponse("tags.html", {"request": request, "book": book})


@router.post("/batch_action")
def batch_action(
    request: Request,
    book_service: BookServiceDependency,
    action: str = Form(...),
    book_ids: list[int] = Form(...),
    tags: str = Form(default=""),
):
    if action == "delete":
        with book_service.transaction():
            book_service.delete_books(book_ids)
    elif action == "update_tags":
        tag_names = [tag.strip().lower() for tag in tags.split(",") if tag.strip()]
        book_service.merge_tags(book_ids, tag_names)

    return RedirectResponse(request.url_for("homepage"), status_code=status.HTTP_303_SEE_OTHER)