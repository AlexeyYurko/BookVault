from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.importers.pipeline import PipelineStep

if TYPE_CHECKING:
    from app.services.importers.context import ImportContext


class PublisherResolutionStep(PipelineStep):
    def process(self, ctx: ImportContext) -> ImportContext:
        if ctx.metadata is None:
            return ctx

        if not ctx.metadata.publisher:
            return ctx
        publisher_name = ctx.metadata.publisher.strip()
        ctx.db_publisher = ctx.store.publisher_repo.get_or_create(name=publisher_name)
        return ctx
