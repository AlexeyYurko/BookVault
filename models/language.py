from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from db.base import Base


class Language(Base):
    __tablename__ = 'languages'

    code = Column(String, primary_key=True)
    name = Column(String, nullable=False)

    books = relationship("Book", backref="language")
