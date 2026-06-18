from fastapi import APIRouter, Request

from app.handlers.dependencies import DataStoreDependency
from app.template_utils import templates

router = APIRouter()


@router.get("/")
def homepage(
    request: Request,
    store: DataStoreDependency,
):
    books = store.book_repo.get_all_books()
    tags = store.book_repo.get_tags_linked_to_books()
    return templates.TemplateResponse("index.html", {"request": request, "books": books, "tags": tags})
