from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.services.importers.pipeline import PipelineStep

if TYPE_CHECKING:
    from app.services.importers.context import ImportContext


class KeywordEnrichmentStep(PipelineStep):
    def process(self, ctx: ImportContext) -> ImportContext:
        if ctx.metadata is None:
            return ctx

        keywords = ctx.store.keyword_tag_repo.get_all_keywords()
        if not keywords:
            return ctx

        keywords.sort(key=len, reverse=True)
        keyword_pattern = re.compile(
            rf"(?<!\w)({'|'.join(re.escape(kw) for kw in keywords)})(?!\w)", re.IGNORECASE
        )

        parts = []
        if ctx.metadata.title is not None:
            parts.append(str(ctx.metadata.title))
        if ctx.metadata.description is not None:
            parts.append(str(ctx.metadata.description))
        text = " ".join(parts).lower()
        if not text:
            return ctx

        ctx.tags.update(m.group(0).lower() for m in keyword_pattern.finditer(text))
        return ctx
