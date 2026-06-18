from __future__ import annotations

from typing import TYPE_CHECKING

from app.models.language import Language
from app.services.importers.pipeline import PipelineStep

if TYPE_CHECKING:
    from app.services.importers.context import ImportContext


class LanguageResolutionStep(PipelineStep):
    def process(self, ctx: ImportContext) -> ImportContext:
        if ctx.metadata is None:
            return ctx

        lang_code = (ctx.metadata.languages or ["en"])[0]
        language = ctx.store.session.query(Language).filter(Language.code == lang_code).first()
        if not language:
            language = Language(code=lang_code, name=lang_code)
            ctx.store.session.add(language)
        ctx.language = language
        return ctx
