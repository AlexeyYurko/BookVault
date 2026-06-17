from fastapi import (
    Depends,
)

from app.db import (
    Session,
    get_db_session,
)
from app.repositories.data_store import DataStore
from app.services.sync_service import SyncService


def get_data_store(db_session: Session = Depends(get_db_session)) -> DataStore:
    return DataStore(db_session)


def get_sync_service() -> SyncService:
    return SyncService()
