import hashlib
import logging
import re
from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.models import Book
from app.models.language import Language
from app.repositories.data_store import DataStore
from app.services.importers.exceptions import ImportBookException

escaping_table = str.maketrans({"#": "sharp"})

logger = logging.getLogger(__name__)


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
    _keyword_cache: list[str] | None = None
    _keyword_pattern: re.Pattern | None = None

    def __init__(self, file, tags, file_path: str | None = None):
        self.file = file
        self.tags = tags
        self.file_path = file_path
        self._checksum: str | None = None

    @abstractmethod
    def extract_cover(self):
        pass

    @abstractmethod
    def get_metadata(self):
        pass

    @property
    def _cover_filename(self):
        return self._calculate_checksum()[:16] + ".jpg"

    def _calculate_checksum(self):
        if self._checksum is not None:
            return self._checksum
        file_hash = hashlib.blake2b()
        f = self.file.file
        f.seek(0)
        while chunk := f.read(8192):
            file_hash.update(chunk)
        self._checksum = file_hash.hexdigest()
        return self._checksum

    def _process_tags(self, store: DataStore):
        db_tags = []
        for tag in self.tags:
            if not tag:
                continue
            cleaned_tag_name = tag.translate(escaping_table)
            db_tag = store.tag_repo.get_or_create(name=cleaned_tag_name)
            db_tags.append(db_tag)
        return db_tags

    @staticmethod
    def _process_authors(store: DataStore, authors):
        db_authors = []
        for author_name in authors:
            if author_name in [None, ""]:
                continue
            cleaned_author_name = author_name.strip()
            author = store.author_repo.get_or_create(name=cleaned_author_name)
            db_authors.append(author)
        return db_authors

    @staticmethod
    def _process_publisher(store: DataStore, publisher_name):
        if not publisher_name:
            return None
        publisher_name = publisher_name.strip()
        db_publisher = store.publisher_repo.get_or_create(name=publisher_name)
        return db_publisher

    def _derive_path_tags(self) -> set[str]:
        if not self.file_path:
            return set()

        books_dir = Path(settings.books_directory)
        file_path = Path(self.file_path)
        try:
            relative = file_path.relative_to(books_dir)
        except ValueError:
            return set()

        parts = list(relative.parts[:-1])
        root_name = books_dir.name.lower()
        path_tags = set()
        for part in parts:
            tag = part.lower().strip()
            if tag and tag != root_name:
                path_tags.add(tag)
        return path_tags

    def _derive_keyword_tags(self, store: DataStore, title: str | None, description: str | None) -> set[str]:
        if self._keyword_pattern is None:
            keywords = store.keyword_tag_repo.get_all_keywords()
            self._keyword_cache = keywords
            if keywords:
                keywords.sort(key=len, reverse=True)
                self._keyword_pattern = re.compile(
                    rf"(?<!\w)({'|'.join(re.escape(kw) for kw in keywords)})(?!\w)", re.IGNORECASE
                )

        if self._keyword_pattern is None:
            return set()

        text = " ".join(filter(None, [title, description])).lower()
        if not text:
            return set()

        return {m.group(0).lower() for m in self._keyword_pattern.finditer(text)}

    def process(self, store: DataStore) -> bool:
        logger.info("Importing book")
        logger.info("Filename: %s, tags: %s", self.file, self.tags)

        try:
            book_metadata = self.get_metadata()
        except ImportBookException as e:
            logger.error(f"Exception while importing {self.file}, {e}")
            return False

        if book_metadata is None:
            logger.warning("No metadata extracted for %s, skipping", self.file)
            return False

        self.tags.update(self._derive_path_tags())

        self.tags.update(self._derive_keyword_tags(store, book_metadata.title, book_metadata.description))

        checksum = self._calculate_checksum()
        book = store.session.query(Book).filter(Book.checksum == checksum).first()
        if book:
            if self.file_path and book.file_path != self.file_path:
                book.file_path = self.file_path
                logger.info(f"Updated file_path for book {book.id}: {self.file_path}")

            existing_tag_names = {t.name for t in book.tags}
            for tag_name in self.tags:
                if tag_name not in existing_tag_names:
                    tag = store.tag_repo.get_or_create(name=tag_name)
                    store.book_repo.add_tag(book, tag)
            return False

        lang_code = (book_metadata.languages or ["en"])[0]
        language = store.session.query(Language).filter(Language.code == lang_code).first()
        if not language:
            language = Language(code=lang_code, name=lang_code)
            store.session.add(language)

        authors = self._process_authors(store, book_metadata.authors)
        publisher = self._process_publisher(store, book_metadata.publisher)
        cover = self.extract_cover()
        tags = self._process_tags(store)

        store.book_repo.create(
            title=book_metadata.title,
            authors=authors,
            checksum=checksum,
            format=self.FORMAT,
            cover=cover,
            tags=tags,
            language=language,
            publisher=publisher,
            description=book_metadata.description,
            file_path=self.file_path,
        )
        return True
