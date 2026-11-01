from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.importers.pipeline import PipelineStep

if TYPE_CHECKING:
    from app.services.importers.context import ImportContext


class BookCreationStep(PipelineStep):
    def process(self, ctx: ImportContext) -> ImportContext:
        if ctx.metadata is None:
            return ctx

        ctx.book = ctx.store.book_repo.create(
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
            isbn=ctx.metadata.isbn,
            original_isbn=ctx.metadata.original_isbn,
            file_path=ctx.importer.file_path,
            catalog_id=ctx.importer.catalog.id,
            publication_name=getattr(ctx, "book_publication_name", None) or (ctx.metadata.title if getattr(ctx.importer.catalog, "kind", None) == "magazine" else None),
            issue_number=getattr(ctx, "book_issue_number", None),
            issue_year=getattr(ctx, "book_issue_year", None),
            issue_month=getattr(ctx, "book_issue_month", None),
            issue_label=getattr(ctx, "book_issue_label", None),
        )
        ctx.store.session.flush()
        return ctx
