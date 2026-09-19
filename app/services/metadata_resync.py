from __future__ import annotations

import logging
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

from app.services.importers.filesystem import PathImporter

if TYPE_CHECKING:
    from app.models import Book
    from app.repositories.data_store import DataStore

logger = logging.getLogger(__name__)

FIELD_LABELS = {
    "title": "Title",
    "description": "Description",
    "isbn": "ISBN",
    "original_isbn": "Original ISBN",
    "edition": "Edition",
    "language": "Language",
    "authors": "Authors",
    "publisher": "Publisher",
    "tags": "Tags",
}


def mark_fields_updated(book: Book, fields: Iterable[str]) -> None:
    current = set(book.manually_updated_fields or [])
    current.update(field for field in fields if field in FIELD_LABELS)
    book.manually_updated_fields = sorted(current)


def reset_field_protection(book: Book) -> None:
    book.manually_updated_fields = []


def resync_book_metadata(store: DataStore, book: Book) -> str | None:
    """Re-extract metadata from ``book.file_path`` and update the record in place.

    Returns ``None`` on success, or an outcome code otherwise:
    ``no_file``, ``missing_file``, ``unsupported``, ``failed``.
    """
    if not book.file_path:
        return "no_file"

    file_path = Path(book.file_path)
    if not file_path.is_file():
        return "missing_file"

    try:
        importer = PathImporter(file_path, set())
    except ValueError:
        logger.warning("Unsupported file extension for resync: %s", book.file_path)
        return "unsupported"

    with store.transaction():
        ok = importer.resync(store, book)

    return None if ok else "failed"