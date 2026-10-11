from typing import Annotated

from fastapi import (
    Depends,
)

from app.db import (
    Session,
    get_db_session,
)
from app.repositories.data_store import DataStore
from app.services.book_service import BookService
from app.services.sync_service import SyncService


def get_data_store(db_session: Session = Depends(get_db_session)) -> DataStore:
    return DataStore(db_session)


DataStoreDependency = Annotated[DataStore, Depends(get_data_store)]


def get_book_service(store: DataStoreDependency) -> BookService:
    return BookService(store)


BookServiceDependency = Annotated[BookService, Depends(get_book_service)]


_sync_service = SyncService()


def get_sync_service() -> SyncService:
    return _sync_service


SyncServiceDependency = Annotated[SyncService, Depends(get_sync_service)]
