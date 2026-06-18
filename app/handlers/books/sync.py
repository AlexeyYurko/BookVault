import logging

from fastapi import APIRouter, Request
from starlette import status
from starlette.responses import RedirectResponse

from app.handlers.dependencies import DataStoreDependency, SyncServiceDependency

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/sync")
def sync_books(
    request: Request,
    sync_service: SyncServiceDependency,
):
    logger.info("Sync requested")
    result = sync_service.run()

    parts = [f"Synced: {result.added} added, {result.skipped} skipped"]
    if result.errors:
        parts.append(f"{len(result.errors)} errors")

    logger.info("Redirecting with result: %s", ", ".join(parts))
    url = request.url_for("homepage").include_query_params(sync_msg=", ".join(parts))
    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)
