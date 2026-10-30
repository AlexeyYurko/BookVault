from fastapi import APIRouter, Request

from app.handlers.dependencies import BookServiceDependency
from app.template_utils import TagSource, render_catalog

router = APIRouter()


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
    )
