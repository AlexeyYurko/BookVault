from starlette.requests import Request
from starlette.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

ALLOWED_PER_PAGE = (20, 50, 100)
DEFAULT_PER_PAGE = 20


class Pagination:
    def __init__(  # noqa: PLR0913
        self,
        *,
        request: Request,
        route_name: str,
        page: int,
        per_page: int,
        total: int,
        route_kwargs: dict | None = None,
        extra_query: dict | None = None,
    ):
        self.request = request
        self.route_name = route_name
        self.route_kwargs = route_kwargs or {}
        self.page = page
        self.per_page = per_page
        self.total = total
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

    def url_for(self, page: int, per_page: int | None = None) -> str:
        params = {**self._extra_query, "page": page, "per_page": per_page if per_page is not None else self.per_page}
        url = self.request.url_for(self.route_name, **self.route_kwargs)
        return str(url.include_query_params(**params))


def normalize_pagination(page: int | None, per_page: int | None) -> tuple[int, int]:
    p = max(1, page or 1)
    size = per_page if per_page in ALLOWED_PER_PAGE else DEFAULT_PER_PAGE
    return p, size