from starlette.requests import Request
from starlette.templating import Jinja2Templates

from app.repositories.book_repository import (
    DEFAULT_SORT_BY,
    DEFAULT_SORT_ORDER,
    SORTABLE_COLUMNS,
)

templates = Jinja2Templates(directory="templates")

ALLOWED_PER_PAGE = (20, 50, 100)
DEFAULT_PER_PAGE = 20

ALLOWED_SORT_ORDERS = ("asc", "desc")


class Pagination:
    def __init__(  # noqa: PLR0913
        self,
        *,
        request: Request,
        route_name: str,
        page: int,
        per_page: int,
        total: int,
        sort_by: str,
        sort_order: str,
        route_kwargs: dict | None = None,
        extra_query: dict | None = None,
    ):
        self.request = request
        self.route_name = route_name
        self.route_kwargs = route_kwargs or {}
        self.page = page
        self.per_page = per_page
        self.total = total
        self.sort_by = sort_by
        self.sort_order = sort_order
        self._extra_query = extra_query or {}

    @property
    def total_pages(self) -> int:
        if self.total == 0:
            return 1
        return (self.total + self.per_page - 1) // self.per_page

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    def _build_url(self, **overrides) -> str:
        params = {
            **self._extra_query,
            "page": self.page,
            "per_page": self.per_page,
            "sort_by": self.sort_by,
            "order": self.sort_order,
            **overrides,
        }
        url = self.request.url_for(self.route_name, **self.route_kwargs)
        return str(url.include_query_params(**params))

    def url_for(self, page: int, per_page: int | None = None) -> str:
        return self._build_url(page=page, per_page=per_page if per_page is not None else self.per_page)

    def sort_url(self, column: str) -> str:
        # clicking the active column toggles direction; a new column starts asc.
        # Resetting to page 1 keeps results stable across sort changes.
        new_order = ("asc" if self.sort_order == "desc" else "desc") if column == self.sort_by else "asc"
        return self._build_url(sort_by=column, order=new_order, page=1)

    def is_sorted(self, column: str) -> bool:
        return column == self.sort_by


def normalize_pagination(
    page: int | None,
    per_page: int | None,
) -> tuple[int, int]:
    p = max(1, page or 1)
    size = per_page if per_page in ALLOWED_PER_PAGE else DEFAULT_PER_PAGE
    return p, size


def normalize_sort(
    sort_by: str | None,
    order: str | None,
) -> tuple[str, str]:
    by = sort_by if sort_by in SORTABLE_COLUMNS else DEFAULT_SORT_BY
    direction = order if order in ALLOWED_SORT_ORDERS else DEFAULT_SORT_ORDER
    return by, direction
