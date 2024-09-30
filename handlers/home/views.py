from fastapi import (
    APIRouter,
    Depends,
    Request,
)
from starlette.templating import Jinja2Templates

from handlers.home.dependencies import (
    get_all_books,
    get_tags_linked_to_books,
)
from models import (
    Book,
    Tag,
)

router = APIRouter()

templates = Jinja2Templates(directory="templates")


@router.get("/")
def homepage(
        request: Request,
        books: list[Book] = Depends(get_all_books),
        tags: list[Tag] = Depends(get_tags_linked_to_books),
):
    return templates.TemplateResponse('index.html', {'request': request, 'books': books, 'tags': tags})
