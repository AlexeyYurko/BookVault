from fastapi import (
    APIRouter,
    Depends,
    Request,
)
from starlette.templating import Jinja2Templates

from app.handlers.dependencies import get_uow

router = APIRouter()

templates = Jinja2Templates(directory="templates")


@router.get("/")
def homepage(
        request: Request,
        uow=Depends(get_uow),
):
    books = uow.book_repo.get_all_books()
    tags = uow.book_repo.get_tags_linked_to_books()
    return templates.TemplateResponse('index.html', {'request': request, 'books': books, 'tags': tags})
