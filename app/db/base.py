from sqlalchemy import create_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    scoped_session,
    sessionmaker,
)

from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={'check_same_thread': False, 'timeout': 30.0},
    echo=False,
)


Session = scoped_session(sessionmaker(bind=engine, autoflush=False))

class Base(DeclarativeBase):
    pass
