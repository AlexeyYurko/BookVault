from fastapi import APIRouter, Request

from app.handlers.dependencies import BookServiceDependency
from app.template_utils import (
    extract_filters,
    normalize_pagination,
    normalize_sort,
    render_book_list,
)

router = APIRouter()


@router.get("/")
def homepage(  # noqa: PLR0913
    request: Request,
    book_service: BookServiceDependency,
    page: int | None = None,
    per_page: int | None = None,
    sort_by: str | None = None,
    order: str | None = None,
):
    page, per_page_size = normalize_pagination(page, per_page)
    sort_by, sort_order = normalize_sort(sort_by, order)
    filters = extract_filters(request.query_params)
    books, total, page = book_service.get_all_books(
        page=page, per_page=per_page_size, sort_by=sort_by, order=sort_order, filters=filters
    )
    filter_context = book_service.filter_context()
    return render_book_list(
        request,
        context={
            "books": books,
            "tags": book_service.get_tags_linked_to_books(),
            "edition_siblings": book_service.edition_siblings_map(books),
            "active_filters": filters,
            **filter_context,
        },
        route_name="homepage",
        page=page,
        per_page=per_page_size,
        total=total,
        sort_by=sort_by,
        sort_order=sort_order,
        extra_query=filters or None,
    )