from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.importers.pipeline import PipelineStep

if TYPE_CHECKING:
    from app.services.importers.context import ImportContext

escaping_table = str.maketrans({"#": "sharp"})


class TagResolutionStep(PipelineStep):
    def process(self, ctx: ImportContext) -> ImportContext:
        db_tags = []
        for tag in ctx.tags:
            if not tag:
                continue
            cleaned_tag_name = tag.translate(escaping_table)
            db_tag = ctx.store.tag_repo.get_or_create(name=cleaned_tag_name)
            db_tags.append(db_tag)
        ctx.db_tags = db_tags
        return ctx
