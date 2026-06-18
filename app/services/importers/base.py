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
            ExtractMetadataStep(),
            PathTagEnrichmentStep(),
            KeywordEnrichmentStep(),
            EditionExtractionStep(),
            DeduplicationStep(),
            LanguageResolutionStep(),
            AuthorResolutionStep(),
            PublisherResolutionStep(),
            CoverExtractionStep(),
            TagResolutionStep(),
            BookCreationStep(),
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
