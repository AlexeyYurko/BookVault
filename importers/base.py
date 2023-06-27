import hashlib
import logging
import os
from abc import abstractmethod

from sqlalchemy.orm import Session

from db.base import engine
from models import (
    Book,
    Tag,
)
from models.author import Author
from models.language import Language


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
    def _cover_filename(self):
        # TODO replace to unique name
        return os.path.splitext(self.file.filename)[0] + ".jpg"

    def _calculate_checksum(self):
        file_hash = hashlib.blake2b()
        while chunk := self.file.file.read(8192):
            file_hash.update(chunk)
        return file_hash.hexdigest()

    def _process_tags(self):
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

    def _process_authors(self, author_names):
        author_names = author_names.split(', ')
        if not author_names:
            author_names = ['unknown']
        db_authors = []
        with Session(bind=engine) as session:
            for author_name in author_names:
                author_name = author_name.strip()
                author = session.query(Author).filter(Author.name == author_name).first()
                if not author:
                    author = Author(name=author_name)
                db_authors.append(author)
        return db_authors

    def process(self):
        logging.info("Importing book")
        logging.info("Filename: %s, tags: %s", self.file, self.tags)
        author_names, title = self.get_metadata()

        checksum = self._calculate_checksum()
        with Session(bind=engine) as session:
            book = session.query(Book).filter(Book.checksum == checksum).first()
            if book:
                # TODO return something like Book Exists
                return
            language = session.query(Language).filter(Language.code == 'en').first()
            book = Book(
                title=title,
                authors=self._process_authors(author_names),
                checksum=checksum,
                format=self.FORMAT,
                cover=self.extract_cover(),
                tags=self._process_tags(),
                language=language
            )
            session.add(book)
            session.commit()
