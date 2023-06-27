from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, DeclarativeBase

engine = create_engine('sqlite:///./bookvault.db', connect_args={'check_same_thread': False}, echo=False)
Session = scoped_session(sessionmaker(bind=engine, autoflush=False))

class Base(DeclarativeBase):
    pass
