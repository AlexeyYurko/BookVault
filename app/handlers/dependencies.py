from typing import Annotated

from fastapi import (
    Depends,
    Form,
    HTTPException,
)
from starlette import status

from app.db import (
    Session,
    get_db_session,
)
from app.models import Book
from app.repositories.data_store import DataStore
from app.services.book_service import BookService
from app.services.sync_service import SyncService


def get_data_store(db_session: Session = Depends(get_db_session)) -> DataStore:
    return DataStore(db_session)


DataStoreDependency = Annotated[DataStore, Depends(get_data_store)]


def get_book_service(store: DataStoreDependency) -> BookService:
    return BookService(store)


BookServiceDependency = Annotated[BookService, Depends(get_book_service)]


def get_book_or_404(book_id: int, book_service: BookServiceDependency) -> Book:
    book = book_service.get_book_by_id(book_id)
    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id={book_id} not found",
        )
    return book


BookDependency = Annotated[Book, Depends(get_book_or_404)]


def get_target_book_or_404(
    book_service: BookServiceDependency,
    target_book_id: int = Form(...),
) -> Book:
    book = book_service.get_book_by_id(target_book_id)
    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id={target_book_id} not found",
        )
    return book


TargetBookDependency = Annotated[Book, Depends(get_target_book_or_404)]


def get_readable_book_or_404(book_id: int, book_service: BookServiceDependency) -> Book:
    book = book_service.get_book_by_id(book_id)
    if book is None or not book.file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return book


ReadableBookDependency = Annotated[Book, Depends(get_readable_book_or_404)]


sync_service = SyncService()


def get_sync_service() -> SyncService:
    return sync_service


SyncServiceDependency = Annotated[SyncService, Depends(get_sync_service)]
