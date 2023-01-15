from fastapi import APIRouter

from .books.views import router as books_router
from .home.views import router as home_router
from .database.views import router as db_router


handlers_router = APIRouter()
handlers_router.include_router(db_router, prefix="/db", tags=["Database"])
handlers_router.include_router(books_router, prefix="/books", tags=["Books"])
handlers_router.include_router(home_router, prefix="", tags=["Home"])
