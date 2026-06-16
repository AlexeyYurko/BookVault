from fastapi import (
    Depends,
)

from app.db import (
    Session,
    get_db_session,
)
from app.repositories.data_store import DataStore


def get_data_store(db_session: Session = Depends(get_db_session)):
    return DataStore(db_session)
