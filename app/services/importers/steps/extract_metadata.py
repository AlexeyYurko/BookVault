from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.services.importers.exceptions import ImportBookException
from app.services.importers.pipeline import PipelineStep

if TYPE_CHECKING:
    from app.services.importers.context import ImportContext

logger = logging.getLogger(__name__)


class ExtractMetadataStep(PipelineStep):
    def process(self, ctx: ImportContext) -> ImportContext | None:
        try:
            ctx.metadata = ctx.importer.get_metadata()
        except ImportBookException as e:
            logger.error("Exception while importing %s, %s", ctx.importer.file, e)
            return None

        if ctx.metadata is None:
            logger.warning("No metadata extracted for %s, skipping", ctx.importer.file)
            return None

        return ctx
