from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.importers.pipeline import PipelineStep

if TYPE_CHECKING:
    from app.services.importers.context import ImportContext


class CoverExtractionStep(PipelineStep):
    def process(self, ctx: ImportContext) -> ImportContext:
        ctx.cover = ctx.importer.extract_cover()
        return ctx
