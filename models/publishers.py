from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from db.base import Base


class Publisher(Base):
    __tablename__ = 'publishers'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    books = relationship("Book", backref="publisher")
