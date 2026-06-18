from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.models import Book
    from app.repositories.data_store import DataStore
    from app.services.importers.base import BookImporter, BookMetadata


@dataclass
class ImportContext:
    store: DataStore
    importer: BookImporter
    metadata: BookMetadata | None = None
    tags: set[str] = field(default_factory=set)
    checksum: str | None = None
    db_authors: list[Any] = field(default_factory=list)
    db_publisher: Any | None = None
    db_tags: list[Any] = field(default_factory=list)
    language: Any | None = None
    cover: str | None = None
    is_new: bool = True
    existing_book: Book | None = None
