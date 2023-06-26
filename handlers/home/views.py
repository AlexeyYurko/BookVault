from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from starlette.templating import Jinja2Templates

from db import get_db_session
from models import Book, Tag

router = APIRouter()

templates = Jinja2Templates(directory="templates")


@router.get("/")
def homepage(request: Request, db_session: Session = Depends(get_db_session)):
    books = db_session.query(Book).all()
    tags = db_session.query(Tag).all()
    return templates.TemplateResponse('index.html', {'request': request, 'books': books, 'tags': tags})
