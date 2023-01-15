from fastapi import APIRouter, Request
from sqlalchemy.orm import Session
from starlette.templating import Jinja2Templates

from db.base import engine
from models import Book, Tag

router = APIRouter()

templates = Jinja2Templates(directory="templates")


@router.get("/")
def homepage(request: Request):
    with Session(bind=engine) as session:
        books = session.query(Book).all()
        tags = session.query(Tag).all()
    return templates.TemplateResponse('index.html', {'request': request, 'books': books, 'tags': tags})
