from fastapi import APIRouter, Query, Request

from app.handlers.dependencies import BookServiceDependency
from app.template_utils import TagSource, render_catalog, templates

router = APIRouter()

READING_SHELF_LIMIT = 10


@router.get("/")
def homepage(request: Request, book_service: BookServiceDependency, query: str = "", tags: str = ""):
    tag_names = [tag.strip().lower() for tag in tags.split(",") if tag.strip()]
    extra_query = {key: value for key, value in {"query": query, "tags": tags}.items() if value}
    return render_catalog(
        request,
        book_service,
        route_name="homepage",
        query=query,
        tags=tag_names,
        tag_source=TagSource.RELATED if tag_names else TagSource.ALL,
        extra_query=extra_query,
        reading_shelf=True,
    )


@router.get("/reading-shelf")
def reading_shelf(
    request: Request,
    book_service: BookServiceDependency,
    show_all: bool = Query(default=False, alias="all"),
):
    books, total = book_service.reading_shelf(limit=None if show_all else READING_SHELF_LIMIT)
    return templates.TemplateResponse(
        request,
        "partials/reading_shelf.html",
        {
            "request": request,
            "reading_books": books,
            "reading_total": total,
            "reading_expanded": show_all,
        },
    )
