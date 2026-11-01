from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.models import Book
from app.services.catalog_paths import PathOutsideCatalogError, resolve_book_file
from app.services.importers.pipeline import PipelineStep

if TYPE_CHECKING:
    from app.services.importers.context import ImportContext

logger = logging.getLogger(__name__)


class DeduplicationStep(PipelineStep):
    def process(self, ctx: ImportContext) -> ImportContext | None:
        ctx.checksum = ctx.importer._calculate_checksum()

        book = (
            ctx.store.session.query(Book)
            .filter(Book.checksum == ctx.checksum, Book.catalog_id == ctx.importer.catalog.id)
            .first()
        )
        if not book:
            return ctx

        ctx.existing_book = book
        ctx.is_new = False

        if ctx.importer.file_path and book.file_path != ctx.importer.file_path and self._should_update_path(book):
            book.file_path = ctx.importer.file_path
            logger.info("Updated file_path for book %s: %s", book.id, ctx.importer.file_path)

        logger.info("Skipping duplicate book %s (checksum %s...)", book.id, ctx.checksum[:8])
        return None

    @staticmethod
    def _should_update_path(book: Book) -> bool:
        if not book.file_path:
            return True
        try:
            return not resolve_book_file(book).is_file()
        except (OSError, PathOutsideCatalogError):
            return True
