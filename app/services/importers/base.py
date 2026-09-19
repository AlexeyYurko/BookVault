import hashlib
import logging
from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.services.importers.context import ImportContext
from app.services.importers.pipeline import run_pipeline
from app.services.importers.steps import (
    AuthorResolutionStep,
    BookCreationStep,
    CoverExtractionStep,
    DeduplicationStep,
    EditionExtractionStep,
    EditionGroupStep,
    ExtractMetadataStep,
    KeywordEnrichmentStep,
    LanguageResolutionStep,
    PathTagEnrichmentStep,
    PublisherResolutionStep,
    TagResolutionStep,
)

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
    isbn: str | None = None
    original_isbn: str | None = None


class BookImporter:
    FORMAT = None

    def __init__(self, file, tags, file_path: str | None = None):
        self.file = file
        self.tags = tags
        self.file_path = file_path
        self._checksum: str | None = None

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

    @abstractmethod
    def extract_cover(self):
        pass

    @abstractmethod
    def get_metadata(self):
        pass

    @classmethod
    def get_pipeline(cls):
        return [
            DeduplicationStep(),
            *cls.get_resync_pipeline(),
            BookCreationStep(),
            EditionGroupStep(),
        ]

    @classmethod
    def get_resync_pipeline(cls):
        return [
            ExtractMetadataStep(),
            PathTagEnrichmentStep(),
            KeywordEnrichmentStep(),
            EditionExtractionStep(),
            LanguageResolutionStep(),
            AuthorResolutionStep(),
            PublisherResolutionStep(),
            CoverExtractionStep(),
            TagResolutionStep(),
        ]

    def process(self, store) -> bool:
        logger.info("Importing book")
        logger.info("Filename: %s, tags: %s", self.file, self.tags)

        ctx = ImportContext(
            store=store,
            importer=self,
            tags=set(self.tags),
        )
        return run_pipeline(self.get_pipeline(), ctx)

    def resync(self, store, book) -> bool:
        """Re-extract metadata from the file and apply it to an existing record."""
        logger.info("Resyncing metadata for book %s from %s", book.id, self.file_path)

        ctx = ImportContext(
            store=store,
            importer=self,
            tags=set(self.tags),
        )
        ctx.checksum = self._calculate_checksum()
        ok = run_pipeline(self.get_resync_pipeline(), ctx)
        if not ok or ctx.metadata is None:
            logger.warning("Resync failed for book %s (%s)", book.id, self.file_path)
            return False

        protected = set(book.manually_updated_fields or [])
        if "title" not in protected:
            book.title = ctx.metadata.title
        if "description" not in protected:
            book.description = ctx.metadata.description
        if "isbn" not in protected:
            book.isbn = ctx.metadata.isbn
        if "original_isbn" not in protected:
            book.original_isbn = ctx.metadata.original_isbn
        if "edition" not in protected:
            book.edition = ctx.edition
        if "language" not in protected:
            book.language = ctx.language
        if "authors" not in protected:
            book.authors = ctx.db_authors
        if "publisher" not in protected:
            book.publisher = ctx.db_publisher
        if "tags" not in protected:
            book.tags = ctx.db_tags
        book.format = self.FORMAT
        book.checksum = ctx.checksum
        book.cover = ctx.cover
        book.file_path = self.file_path
        store.session.flush()
        return True
