from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from app.services.importers.pipeline import PipelineStep

if TYPE_CHECKING:
    from app.services.importers.context import ImportContext

EDITION_PATTERNS = [
    r"(\d+)(?:st|nd|rd|th)\s+Edition",
    r"(\d+)(?:st|nd|rd|th)\s+[Ee]d(?=\.|\s|$)",
    r"Edition\s+(\d+)",
]


class EditionExtractionStep(PipelineStep):
    def process(self, ctx: ImportContext) -> ImportContext:
        if ctx.metadata is None:
            return ctx

        filename = Path(ctx.importer.file_path).name if ctx.importer.file_path else getattr(ctx.importer.file, "filename", None)

        for text in filter(None, [ctx.metadata.title, ctx.metadata.description, filename]):
            for pattern in EDITION_PATTERNS:
                match = re.search(pattern, text)
                if match:
                    ctx.edition = match.group(0)
                    return ctx

        return ctx
