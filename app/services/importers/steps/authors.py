from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.importers.pipeline import PipelineStep

if TYPE_CHECKING:
    from app.services.importers.context import ImportContext


class AuthorResolutionStep(PipelineStep):
    def process(self, ctx: ImportContext) -> ImportContext:
        if ctx.metadata is None:
            return ctx

        db_authors = []
        for author_name in ctx.metadata.authors:
            if author_name in [None, ""]:
                continue
            cleaned_author_name = author_name.strip()
            author = ctx.store.author_repo.get_or_create(name=cleaned_author_name)
            db_authors.append(author)
        ctx.db_authors = db_authors
        return ctx
