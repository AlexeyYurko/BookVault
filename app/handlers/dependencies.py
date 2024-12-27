from fastapi import (
    Depends,
)

from app.db import (
    Session,
    get_db_session,
)
from app.repositories.uow import UnitOfWork


def get_uow(db_session: Session = Depends(get_db_session)):
    return UnitOfWork(db_session)
