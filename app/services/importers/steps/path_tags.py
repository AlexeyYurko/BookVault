from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from app.config import settings
from app.services.importers.pipeline import PipelineStep

if TYPE_CHECKING:
    from app.services.importers.context import ImportContext


class PathTagEnrichmentStep(PipelineStep):
    def process(self, ctx: ImportContext) -> ImportContext:
        if not ctx.importer.file_path:
            return ctx

        books_dir = Path(settings.books_directory)
        file_path = Path(ctx.importer.file_path)
        try:
            relative = file_path.relative_to(books_dir)
        except ValueError:
            return ctx

        parts = list(relative.parts[:-1])
        root_name = books_dir.name.lower()
        for part in parts:
            tag = part.lower().strip()
            if tag and tag != root_name:
                ctx.tags.add(tag)

        return ctx
