from fastapi import APIRouter, Request

from app.handlers.dependencies import BookServiceDependency
from app.template_utils import TagSource, render_catalog

router = APIRouter()


@router.get("/")
def homepage(request: Request, book_service: BookServiceDependency):
    return render_catalog(request, book_service, route_name="homepage", tag_source=TagSource.ALL)
