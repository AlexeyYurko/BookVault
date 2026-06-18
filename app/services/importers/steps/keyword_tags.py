from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.services.importers.pipeline import PipelineStep

if TYPE_CHECKING:
    from app.services.importers.context import ImportContext


class KeywordEnrichmentStep(PipelineStep):
    _keyword_cache: list[str] | None = None
    _keyword_pattern: re.Pattern | None = None

    def process(self, ctx: ImportContext) -> ImportContext:
        if ctx.metadata is None:
            return ctx

        if self._keyword_pattern is None:
            keywords = ctx.store.keyword_tag_repo.get_all_keywords()
            self._keyword_cache = keywords
            if keywords:
                keywords.sort(key=len, reverse=True)
                self._keyword_pattern = re.compile(
                    rf"(?<!\w)({'|'.join(re.escape(kw) for kw in keywords)})(?!\w)", re.IGNORECASE
                )

        if self._keyword_pattern is None:
            return ctx

        text = " ".join(filter(None, [ctx.metadata.title, ctx.metadata.description])).lower()
        if not text:
            return ctx

        ctx.tags.update(m.group(0).lower() for m in self._keyword_pattern.finditer(text))
        return ctx
