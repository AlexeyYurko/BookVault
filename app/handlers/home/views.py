from fastapi import APIRouter, Depends, Request

from app.handlers.dependencies import get_data_store
from app.template_utils import templates

router = APIRouter()


@router.get("/")
def homepage(
        request: Request,
        store=Depends(get_data_store),
):
    books = store.book_repo.get_all_books()
    tags = store.book_repo.get_tags_linked_to_books()
    return templates.TemplateResponse('index.html', {'request': request, 'books': books, 'tags': tags})
