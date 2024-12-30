import hashlib
import logging
import os
from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.base import engine
from app.models import (
    Book,
)
from app.models.language import Language
from app.repositories.uow import UnitOfWork
from app.services.importers.exceptions import ImportBookException

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

    def _process_tags(self, uow: UnitOfWork):
        db_tags = []
        for tag in self.tags:
            if not tag:
                continue
            cleaned_tag_name = tag.translate(escaping_table)
            db_tag = uow.tag_repo.get_or_create(name=cleaned_tag_name)
            db_tags.append(db_tag)
        return db_tags

    @staticmethod
    def _process_authors(uow: UnitOfWork, authors):
        db_authors = []
        for author_name in authors:
            if author_name in [None, '']:
                continue
            cleaned_author_name = author_name.strip()
            author = uow.author_repo.get_or_create(name=cleaned_author_name)
            db_authors.append(author)
        return db_authors

    @staticmethod
    def _process_publisher(uow: UnitOfWork, publisher_name):
        if not publisher_name:
            return None
        publisher_name = publisher_name.strip()
        db_publisher = uow.publisher_repo.get_or_create(name=publisher_name)
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
            uow = UnitOfWork(session)
            with uow.transaction():
                book = session.query(Book).filter(Book.checksum == checksum).first()
                if book:
                    # TODO return something like Book Exists
                    return
                # TODO add support for different languages
                language = session.query(Language).filter(Language.code == 'en').first()

                authors = self._process_authors(uow, book_metadata.authors)
                publisher = self._process_publisher(uow, book_metadata.publisher)
                cover = self.extract_cover()
                tags = self._process_tags(uow)

                uow.book_repo.create(
                    title=book_metadata.title,
                    authors=authors,
                    checksum=checksum,
                    format=self.FORMAT,
                    cover=cover,
                    tags=tags,
                    language=language,
                    publisher=publisher,
                    description=book_metadata.description
                )
                session.commit()
