from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.importers.context import ImportContext

logger = logging.getLogger(__name__)


class PipelineStep:
    def process(self, ctx: ImportContext) -> ImportContext | None:
        raise NotImplementedError


def run_pipeline(steps: list[PipelineStep], ctx: ImportContext) -> bool:
    for step in steps:
        logger.debug("Running pipeline step: %s", step.__class__.__name__)
        result = step.process(ctx)
        if result is None:
            return False
        ctx = result
    return True
