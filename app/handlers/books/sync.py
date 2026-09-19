import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from threading import Lock

from fastapi import APIRouter, HTTPException, Request
from starlette import status
from starlette.responses import RedirectResponse

from app.handlers.dependencies import SyncServiceDependency
from app.template_utils import templates

logger = logging.getLogger(__name__)

router = APIRouter()


@dataclass
class SyncTask:
    task_id: str
    total: int = 0
    processed: int = 0
    added: int = 0
    skipped: int = 0
    errors: int = 0
    current_file: str = ""
    done: bool = False
    result_message: str = ""
    _lock: Lock = field(default_factory=Lock)

    def update(self, **kwargs):
        with self._lock:
            for key, value in kwargs.items():
                if key == "result":
                    continue
                setattr(self, key, value)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "task_id": self.task_id,
                "total": self.total,
                "processed": self.processed,
                "added": self.added,
                "skipped": self.skipped,
                "errors": self.errors,
                "current_file": self.current_file,
                "done": self.done,
                "result_message": self.result_message,
            }


# In-memory task registry. Single-process only.
sync_tasks: dict[str, SyncTask] = {}


def _build_result_message(result) -> str:
    parts = [f"Synced: {result.added} added, {result.skipped} skipped"]
    if result.errors:
        parts.append(f"{len(result.errors)} errors")
    return ", ".join(parts)


@router.get("/sync")
def sync_confirm(request: Request):
    return templates.TemplateResponse("sync_confirm.html", {"request": request})


@router.post("/sync")
async def sync_books(
    request: Request,
    sync_service: SyncServiceDependency,
):
    logger.info("Sync requested")
    task_id = uuid.uuid4().hex[:12]
    task = SyncTask(task_id=task_id)
    sync_tasks[task_id] = task

    def on_progress(data: dict):
        task.update(**data)

    async def _run():
        try:
            result = await asyncio.to_thread(sync_service.run, on_progress=on_progress)
            message = _build_result_message(result)
            task.update(done=True, result_message=message)
            logger.info("Redirecting with result: %s", message)
        except Exception:
            logger.exception("Sync task failed")
            task.update(done=True, errors=task.errors + 1, result_message="Sync failed")

    asyncio.create_task(_run())

    url = request.url_for("sync_progress", task_id=task_id)
    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/sync/{task_id}")
def sync_progress(request: Request, task_id: str):
    task = sync_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sync task not found")
    return templates.TemplateResponse("sync_progress.html", {"request": request, "task": task})


@router.get("/sync/{task_id}/progress")
def sync_progress_fragment(request: Request, task_id: str):
    task = sync_tasks.get(task_id)
    return templates.TemplateResponse("sync_progress_fragment.html", {"request": request, "task": task})
