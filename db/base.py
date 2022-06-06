from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

engine = create_engine('sqlite:///./bookvault.db', connect_args={'check_same_thread': False}, echo=False)
Base = declarative_base()
db_session = sessionmaker(bind=engine)()
