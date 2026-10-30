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
from pydantic import BaseModel, Field
from starlette import status

from app.config import settings
from app.handlers.dependencies import (
    BookDependency,
    BookServiceDependency,
    ReadableBookDependency,
    TargetBookDependency,
)
from app.services.book_service import EditBookDTO, ImportedFile
from app.services.metadata_resync import FIELD_LABELS
from app.template_utils import TagSource, render_catalog, templates

BOOK_MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".epub": "application/epub+zip",
    ".djvu": "image/vnd.djvu",
}

READER_FORMATS = {
    ".pdf": "pdf",
    ".epub": "epub",
}


class ReadingProgressPayload(BaseModel):
    position: str | None = Field(default=None, max_length=4000)
    percent: float | None = Field(default=None, ge=0, le=100)


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
def search_books(
    request: Request,
    book_service: BookServiceDependency,
    query: str = Query(default=""),
):
    return render_catalog(
        request,
        book_service,
        route_name="search_books",
        query=query,
        extra_query={"query": query} if query else None,
    )


@router.get("/filter")
def filter_books(
    request: Request,
    book_service: BookServiceDependency,
    tags: str = Query(default=""),
):
    tag_names = [tag.strip().lower() for tag in tags.split(",") if tag.strip()]
    return render_catalog(
        request,
        book_service,
        route_name="filter_books",
        tags=tag_names,
        tag_source=TagSource.RELATED,
        extra_query={"tags": tags},
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
    book: BookDependency,
    book_service: BookServiceDependency,
):
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


@router.get("/{book_id}/read")
def read_book(
    request: Request,
    book: ReadableBookDependency,
):
    reader_format = READER_FORMATS.get(Path(book.file_path).suffix.lower())
    if reader_format is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This format cannot be read in the browser",
        )

    back_url = next_url(request, request.query_params.get("next", "")) or str(request.url_for("homepage"))
    return templates.TemplateResponse(
        "reader.html",
        {
            "request": request,
            "book": book,
            "reader_format": reader_format,
            "back_url": back_url,
        },
    )


@router.put("/{book_id}/progress")
def save_reading_progress(
    book_id: int,
    payload: ReadingProgressPayload,
    book_service: BookServiceDependency,
):
    book = book_service.save_reading_progress(book_id, payload.position, payload.percent)
    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id={book_id} not found",
        )
    return {"status": "ok"}


@router.get("/{book_id}/detail")
def book_detail_panel(
    request: Request,
    book: BookDependency,
):
    back_url = next_url(request, request.headers.get("referer", "")) or str(request.url_for("homepage"))
    return templates.TemplateResponse(
        "book_detail_panel.html",
        {"request": request, "book": book, "back_url": back_url},
    )


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
    book: BookDependency,
    book_service: BookServiceDependency,
):
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
    book: BookDependency,
    book_service: BookServiceDependency,
):
    outcome = book_service.resync_metadata(book)
    url = request.url_for("edit_book", book_id=book.id).include_query_params(resync=outcome or "ok")
    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{book_id}/unprotect")
def unprotect_fields(
    request: Request,
    book: BookDependency,
    book_service: BookServiceDependency,
):
    book_service.unprotect_fields(book)

    url = request.url_for("edit_book", book_id=book.id).include_query_params(resync="unprotected")
    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{book_id}/lookup")
def lookup_metadata(
    request: Request,
    book: BookDependency,
    book_service: BookServiceDependency,
    query: str = Form(default=""),
    next: str = Form(default=""),
):
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
    book: BookDependency,
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

    target = next_url(request, next) or request.url_for("show_book", book_id=book.id)
    return RedirectResponse(target, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{book_id}/editions/search")
def search_link_candidates(
    request: Request,
    book: BookDependency,
    book_service: BookServiceDependency,
    query: str = Query(default=""),
):
    candidates = book_service.find_link_candidates(book, query)
    return templates.TemplateResponse(
        "edition_link_results.html",
        {"request": request, "book": book, "candidates": candidates},
    )


@router.post("/{book_id}/editions/link")
def link_edition(
    request: Request,
    book: BookDependency,
    target: TargetBookDependency,
    book_service: BookServiceDependency,
):
    try:
        book_service.link_edition(book, target)
        outcome = "linked"
    except ValueError:
        outcome = "error"

    url = request.url_for("edit_book", book_id=book.id).include_query_params(edition=outcome)
    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{book_id}/editions/unlink")
def unlink_edition(
    request: Request,
    book: BookDependency,
    book_service: BookServiceDependency,
):
    book_service.unlink_edition(book)

    url = request.url_for("edit_book", book_id=book.id).include_query_params(edition="unlinked")
    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{book_id}/download")
def download_book(
    request: Request,
    book: ReadableBookDependency,
):
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
    book: ReadableBookDependency,
    download: bool = False,
):
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

    media_type = BOOK_MEDIA_TYPES.get(file_path.suffix.lower(), "application/octet-stream")
    return FileResponse(
        str(file_path),
        media_type=media_type,
        filename=file_path.name,
        content_disposition_type="attachment" if download else "inline",
    )


@router.get("/by_tag/{tag_name}")
def show_books_by_tag(
    request: Request,
    tag_name: str,
    book_service: BookServiceDependency,
):
    return render_catalog(
        request,
        book_service,
        route_name="show_books_by_tag",
        tags=[tag_name],
        route_kwargs={"tag_name": tag_name},
    )


@router.post("/{book_id}/tags")
def add_tag(
    request: Request,
    book: BookDependency,
    book_service: BookServiceDependency,
    tag_name: str = Form(...),
):
    with book_service.transaction():
        book_service.add_tag(book, tag_name)

    return templates.TemplateResponse("tags.html", {"request": request, "book": book})


@router.delete("/{book_id}/tags/{tag_id}")
def remove_tag(
    request: Request,
    book: BookDependency,
    tag_id: int,
    book_service: BookServiceDependency,
):
    with book_service.transaction():
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