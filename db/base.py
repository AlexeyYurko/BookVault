from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session

engine = create_engine('sqlite:///./bookvault.db', connect_args={'check_same_thread': False}, echo=False)
Base = declarative_base()
Session = scoped_session(sessionmaker(bind=engine, autoflush=False))
