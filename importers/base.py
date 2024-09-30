import hashlib
import logging
import os
from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from db.base import engine
from importers.exceptions import ImportBookException
from models import (
    Book,
    Tag,
)
from models.author import Author
from models.language import Language
from models.publishers import Publisher

escaping_table = str.maketrans({'#': 'sharp'})

@dataclass
class BookMetadata:
    title: str
    authors: list[str]
    description: str | None
    publisher: str | None
    languages: list[str] | None
    tags: list[str] | None
    published_date: datetime | None


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
        return os.path.splitext(self.file.filename)[0].translate(escaping_table) + ".jpg"

    def _calculate_checksum(self):
        file_hash = hashlib.blake2b()
        self.file.file.seek(0)
        while chunk := self.file.file.read(8192):
            file_hash.update(chunk)
        return file_hash.hexdigest()

    def _process_tags(self):
        db_tags = []
        with Session(bind=engine) as session:
            for tag in self.tags:
                if not tag:
                    continue
                cleaned_tag = tag.translate(escaping_table)
                db_tag = session.query(Tag).filter(Tag.name == cleaned_tag).first() or Tag(name=cleaned_tag)
                db_tags.append(db_tag)
        return db_tags

    @staticmethod
    def _process_authors(authors):
        db_authors = []
        with Session(bind=engine) as session:
            for author_name in authors:
                if author_name in [None, '']:
                    continue
                cleaned_author_name = author_name.strip()
                author = session.query(Author).filter(Author.name == cleaned_author_name).first() or Author(name=cleaned_author_name)
                db_authors.append(author)
        return db_authors

    @staticmethod
    def _process_publisher(publisher):
        if not publisher:
            return None
        with Session(bind=engine) as session:
            publisher = publisher.strip()
            db_publisher = session.query(Publisher).filter(Publisher.name == publisher).first() or Publisher(name=publisher)
        return db_publisher

    def process(self):
        logging.info("Importing book")
        logging.info("Filename: %s, tags: %s", self.file, self.tags)
        try:
            book_metadata = self.get_metadata()
        except ImportBookException as e:
            logging.error(f'Exception while importing {self.file}, {e}')
            return

        checksum = self._calculate_checksum()
        with Session(bind=engine) as session:
            book = session.query(Book).filter(Book.checksum == checksum).first()
            if book:
                # TODO return something like Book Exists
                return
            # TODO add support for different languages
            language = session.query(Language).filter(Language.code == 'en').first()
            book = Book(
                title=book_metadata.title,
                authors=self._process_authors(book_metadata.authors),
                checksum=checksum,
                format=self.FORMAT,
                cover=self.extract_cover(),
                tags=self._process_tags(),
                language=language,
                publisher=self._process_publisher(book_metadata.publisher),
                description=book_metadata.description
            )
            session.add(book)
            session.commit()
