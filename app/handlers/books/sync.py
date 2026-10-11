import asyncio
import logging

from fastapi import APIRouter, HTTPException, Request
from starlette import status
from starlette.responses import RedirectResponse

from app.handlers.dependencies import SyncServiceDependency
from app.template_utils import templates

logger = logging.getLogger(__name__)

router = APIRouter()

_background_tasks: set[asyncio.Task] = set()


@router.get("/sync")
def sync_confirm(request: Request):
    return templates.TemplateResponse("sync_confirm.html", {"request": request})


@router.post("/sync")
async def sync_books(
    request: Request,
    sync_service: SyncServiceDependency,
):
    logger.info("Sync requested")
    task = sync_service.create_task()

    def on_progress(data: dict):
        task.update(**data)

    async def _run():
        try:
            result = await asyncio.to_thread(sync_service.run, on_progress=on_progress)
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