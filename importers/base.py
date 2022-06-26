import hashlib
import logging
import os
from abc import abstractmethod

from sqlalchemy.orm import Session

from db import engine
from models import Book, Tag


class BookImporter:
    FORMAT = None

    def __init__(self, file, tags):
        self.file = file
        self.tags = tags

    @abstractmethod
    def extract_cover(self):
        pass

    @abstractmethod
    def get_metadata(self):
        pass

    @property
    def cover_filename(self):
        # TODO replace to unique name
        return os.path.splitext(self.file.filename)[0] + ".jpg"

    def calculate_checksum(self):
        file_hash = hashlib.blake2b()
        while chunk := self.file.read(8192):
            file_hash.update(chunk)
        return file_hash.hexdigest()

    def process_tags(self):
        db_tags = []
        with Session(bind=engine) as session:
            for tag in self.tags:
                if not tag:
                    continue
                db_tag = session.query(Tag).filter(Tag.name == tag).first()
                if db_tag is None:
                    db_tag = Tag(name=tag)
                db_tags.append(db_tag)
        return db_tags

    def process(self):
        logging.info("Importing book")
        logging.info("Filename: %s, tags: %s", self.file, self.tags)
        author, title = self.get_metadata()
        checksum = self.calculate_checksum()
        with Session(bind=engine) as session:
            book = session.query(Book).filter(Book.checksum == checksum).first()
            if book:
                # TODO return something like Book Exists
                return
            book = Book(
                title=title,
                author=author,
                checksum=checksum,
                format=self.FORMAT,
                cover=self.extract_cover(),
                tags=self.process_tags()
            )
            session.add(book)
            session.commit()
