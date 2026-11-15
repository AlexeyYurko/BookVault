from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.services.importers.exceptions import ImportBookException
from app.services.importers.isbn import canonical_isbn
from app.services.importers.pipeline import PipelineStep
from app.services.importers.text_utils import clean_description

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

        ctx.metadata.description = clean_description(ctx.metadata.description)
        # store one canonical ISBN-13 form in every import/resync path; the
        # original edition ISBN is canonicalized the same way when present
        ctx.metadata.isbn = canonical_isbn(ctx.metadata.isbn)
        ctx.metadata.original_isbn = canonical_isbn(ctx.metadata.original_isbn)

        return ctx
