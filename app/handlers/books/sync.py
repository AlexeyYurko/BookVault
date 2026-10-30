import asyncio
import logging
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Form, HTTPException, Request
from starlette import status
from starlette.responses import RedirectResponse

from app.config import settings
from app.handlers.dependencies import SyncServiceDependency
from app.services.sync_service import ALL_FOLDERS, format_scope
from app.template_utils import templates

logger = logging.getLogger(__name__)

router = APIRouter()

_background_tasks: set[asyncio.Task] = set()


def list_first_level_folders() -> tuple[list[str], str | None]:
    """Return visible first-level folders of the books directory, or an error message."""
    if not settings.books_directory:
        return [], 'BOOKS_DIRECTORY is not set'

    books_dir = Path(settings.books_directory)
    if not books_dir.is_dir():
        return [], f'Books directory not found: {books_dir}'

    try:
        folders = [entry.name for entry in books_dir.iterdir() if entry.is_dir() and not entry.name.startswith('.')]
    except OSError as exc:
        return [], f'Could not read books directory: {exc}'

    return sorted(folders, key=str.lower), None


def _redirect(request: Request, route_name: str, message: str | None = None, **path_params) -> RedirectResponse:
    url = str(request.url_for(route_name, **path_params))
    if message:
        url = f'{url}?{urlencode({"sync_msg": message})}'
    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/sync")
def sync_confirm(request: Request):
    folders, error = list_first_level_folders()
    return templates.TemplateResponse(
        "sync_confirm.html",
        {"request": request, "folders": folders, "error": error, "all_folders_value": ALL_FOLDERS},
    )


@router.get("/sync/folders")
def sync_folder_list(request: Request):
    folders, error = list_first_level_folders()
    return templates.TemplateResponse(
        "_sync_form.html",
        {"request": request, "folders": folders, "error": error, "all_folders_value": ALL_FOLDERS},
    )


@router.post("/sync")
async def sync_books(
    request: Request,
    sync_service: SyncServiceDependency,
    folders: list[str] = Form(default=[]),
):
    if ALL_FOLDERS in folders:
        selected: list[str] | None = None
        scope = 'all folders'
    elif folders:
        selected = folders
        scope = format_scope(folders)
    else:
        return _redirect(request, 'homepage', 'Select at least one folder to sync')

    logger.info("Sync requested: %s", scope)
    task = sync_service.create_task(scope=scope)
    if task is None:
        active = sync_service.get_active_task()
        if active is not None:
            url = str(request.url_for('sync_progress', task_id=active.task_id))
            return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)
        return _redirect(request, 'homepage', 'Sync already running')

    def on_progress(data: dict):
        task.update(**data)

    async def _run():
        try:
            result = await asyncio.to_thread(sync_service.run, selected, on_progress=on_progress)
            message = sync_service.result_message(result)
            task.update(done=True, result_message=message)
            logger.info("Redirecting with result: %s", message)
        except Exception:
            logger.exception("Sync task failed")
            task.bump_errors()
            task.update(done=True, result_message="Sync failed")

    background_task = asyncio.create_task(_run())
    _background_tasks.add(background_task)
    background_task.add_done_callback(_background_tasks.discard)

    url = request.url_for("sync_progress", task_id=task.task_id)
    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/sync/{task_id}")
def sync_progress(request: Request, task_id: str, sync_service: SyncServiceDependency):
    task = sync_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sync task not found")
    return templates.TemplateResponse("sync_progress.html", {"request": request, "task": task})


@router.get("/sync/{task_id}/progress")
def sync_progress_fragment(request: Request, task_id: str, sync_service: SyncServiceDependency):
    task = sync_service.get_task(task_id)
    return templates.TemplateResponse("sync_progress_fragment.html", {"request": request, "task": task})
