import logging

from fastapi import APIRouter, Depends, Request
from starlette import status
from starlette.responses import RedirectResponse

from app.handlers.dependencies import get_data_store, get_sync_service
from app.repositories.data_store import DataStore
from app.services.sync_service import SyncService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get('/sync')
def sync_books(
    request: Request,
    store: DataStore = Depends(get_data_store),
    sync_service: SyncService = Depends(get_sync_service),
):
    logger.info('Sync requested')
    result = sync_service.run(store)

    parts = [f'Synced: {result.added} added, {result.skipped} skipped']
    if result.errors:
        parts.append(f'{len(result.errors)} errors')

    logger.info('Redirecting with result: %s', ', '.join(parts))
    url = request.url_for('homepage').include_query_params(sync_msg=', '.join(parts))
    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)
