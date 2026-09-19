from fastapi import APIRouter, Request

from app.handlers.dependencies import DataStoreDependency
from app.template_utils import (
    DEFAULT_PER_PAGE,
    Pagination,
    build_filter_context,
    extract_filters,
    normalize_pagination,
    normalize_sort,
    templates,
)

router = APIRouter()


@router.get("/")
def homepage(  # noqa: PLR0913
    request: Request,
    store: DataStoreDependency,
    page: int | None = None,
    per_page: int | None = None,
    sort_by: str | None = None,
    order: str | None = None,
):
    page, per_page_size = normalize_pagination(page, per_page)
    sort_by, sort_order = normalize_sort(sort_by, order)
    filters = extract_filters(request.query_params)
    books, total, page = store.book_repo.get_all_books(
        page=page, per_page=per_page_size, sort_by=sort_by, order=sort_order, filters=filters
    )
    tags = store.book_repo.get_tags_linked_to_books()
    pagination = Pagination(
        request=request,
        route_name="homepage",
        page=page,
        per_page=per_page_size,
        total=total,
        sort_by=sort_by,
        sort_order=sort_order,
        extra_query=filters or None,
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