from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.models import Book
from app.services.importers.pipeline import PipelineStep

if TYPE_CHECKING:
    from app.services.importers.context import ImportContext

logger = logging.getLogger(__name__)


class DeduplicationStep(PipelineStep):
    def process(self, ctx: ImportContext) -> ImportContext | None:
        ctx.checksum = ctx.importer._calculate_checksum()

        book = ctx.store.session.query(Book).filter(Book.checksum == ctx.checksum).first()
        if not book:
            return ctx

        ctx.existing_book = book
        ctx.is_new = False

        if ctx.importer.file_path and book.file_path != ctx.importer.file_path:
            book.file_path = ctx.importer.file_path
            logger.info("Updated file_path for book %s: %s", book.id, ctx.importer.file_path)

        if ctx.edition and book.edition != ctx.edition:
            book.edition = ctx.edition
            logger.info("Updated edition for book %s: %s", book.id, ctx.edition)

        existing_tag_names = {t.name for t in book.tags}
        for tag_name in ctx.tags:
            if tag_name not in existing_tag_names:
                tag = ctx.store.tag_repo.get_or_create(name=tag_name)
                if tag is not None:
                    ctx.store.book_repo.add_tag(book, tag)

        return None
