from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from app.services.importers.pipeline import PipelineStep

if TYPE_CHECKING:
    from app.services.importers.context import ImportContext


class PathTagEnrichmentStep(PipelineStep):
    def process(self, ctx: ImportContext) -> ImportContext:
        if not ctx.importer.file_path:
            return ctx

        for part in Path(ctx.importer.file_path).parts[:-1]:
            tag = part.lower().strip()
            if tag:
                ctx.tags.add(tag)

        return ctx
