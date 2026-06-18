from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.importers.pipeline import PipelineStep

if TYPE_CHECKING:
    from app.services.importers.context import ImportContext


class BookCreationStep(PipelineStep):
    def process(self, ctx: ImportContext) -> ImportContext:
        if ctx.metadata is None:
            return ctx

        ctx.store.book_repo.create(
            title=ctx.metadata.title,
            authors=ctx.db_authors,
            checksum=ctx.checksum,
            format=ctx.importer.FORMAT,
            cover=ctx.cover,
            tags=ctx.db_tags,
            language=ctx.language,
            publisher=ctx.db_publisher,
            description=ctx.metadata.description,
            edition=ctx.edition,
            file_path=ctx.importer.file_path,
        )
        return ctx
