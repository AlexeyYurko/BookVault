import asyncio
import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Form, HTTPException, Request
from starlette import status
from starlette.responses import RedirectResponse

from app.handlers.dependencies import CatalogServiceDependency, SyncServiceDependency
from app.services.sync_service import ALL_FOLDERS, format_scope, list_first_level_folders
from app.template_utils import templates

logger = logging.getLogger(__name__)

router = APIRouter()

_background_tasks: set[asyncio.Task] = set()


def _sync_context(catalog_service: CatalogServiceDependency, requested_catalog: str = ""):
    catalogs = catalog_service.list()
    enabled = [catalog for catalog in catalogs if catalog.enabled]
    selected = requested_catalog
    if not selected:
        selected = "all" if enabled else (str(catalogs[0].id) if catalogs else "")
    if selected == "all" and not enabled:
        selected = str(catalogs[0].id) if catalogs else ""

    folders = []
    error = None
    if not catalogs:
        error = "No catalogs configured. Add one in Settings → Catalogs."
        selected = ""
    elif selected == "all":
        pass
    else:
        try:
            catalog_id = int(selected)
        except ValueError:
            catalog_id = 0
        catalog = next((item for item in catalogs if item.id == catalog_id), None)
        if catalog is None:
            error = "Selected catalog not found."
        else:
            folders, error = list_first_level_folders(catalog)
    return {
        "catalogs": catalogs,
        "selected_catalog_id": selected,
        "has_enabled_catalogs": bool(enabled),
        "folders": folders,
        "error": error,
        "all_folders_value": ALL_FOLDERS,
    }


def _redirect(request: Request, route_name: str, message: str | None = None, **path_params) -> RedirectResponse:
    url = str(request.url_for(route_name, **path_params))
    if message:
        url = f'{url}?{urlencode({"sync_msg": message})}'
    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/sync")
def sync_confirm(request: Request, catalog_service: CatalogServiceDependency, catalog_id: str = ""):
    return templates.TemplateResponse(request, 
        "sync_confirm.html",
        {"request": request, **_sync_context(catalog_service, catalog_id)},
    )


@router.get("/sync/folders")
def sync_folder_list(request: Request, catalog_service: CatalogServiceDependency, catalog_id: str = ""):
    return templates.TemplateResponse(request, 
        "_sync_form.html",
        {"request": request, **_sync_context(catalog_service, catalog_id)},
    )


@router.post("/sync")
async def sync_books(
    request: Request,
    sync_service: SyncServiceDependency,
    catalog_service: CatalogServiceDependency,
    catalog_id: str = Form(...),
    folders: list[str] = Form(default=[]),
):
    if catalog_id == "all":
        selected_catalog_id = None
        selected_folders = None
        scope = "all enabled catalogs"
    else:
        try:
            selected_catalog_id = int(catalog_id)
        except ValueError:
            return _redirect(request, "sync_confirm", "Select a catalog to sync")
        catalog = catalog_service.get(selected_catalog_id)
        if catalog is None:
            return _redirect(request, "sync_confirm", "Selected catalog not found")
        if ALL_FOLDERS in folders:
            selected_folders = None
            scope = f"{catalog.name}: all folders"
        elif folders:
            selected_folders = folders
            scope = f"{catalog.name}: {format_scope(folders)}"
        else:
            return _redirect(request, "sync_confirm", "Select at least one folder to sync", catalog_id=catalog_id)

    logger.info("Sync requested: %s", scope)
    task = sync_service.create_task(scope=scope)
    if task is None:
        active = sync_service.get_active_task()
        if active is not None:
            url = str(request.url_for("sync_progress", task_id=active.task_id))
            return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)
        return _redirect(request, "homepage", "Sync already running")

    def on_progress(data: dict):
        task.update(**data)

    async def _run():
        try:
            result = await asyncio.to_thread(
                sync_service.run,
                selected_catalog_id,
                selected_folders,
                on_progress=on_progress,
            )
            message = sync_service.result_message(result)
            task.update(done=True, result_message=message)
            logger.info("Sync completed: %s", message)
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
    return templates.TemplateResponse(request, "sync_progress.html", {"request": request, "task": task})


@router.get("/sync/{task_id}/progress")
def sync_progress_fragment(request: Request, task_id: str, sync_service: SyncServiceDependency):
    task = sync_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sync task not found")
    return templates.TemplateResponse(request, "sync_progress_fragment.html", {"request": request, "task": task})
