from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock

from app.config import settings
from app.db import Session
from app.repositories.data_store import DataStore
from app.services.directory_scanner import DirectoryScanner
from app.services.importers.dedup_guard import release, try_claim
from app.services.importers.filesystem import PathImporter

logger = logging.getLogger(__name__)

MAX_FINISHED_TASKS = 20

ALL_FOLDERS = '__all__'

SCOPE_PREVIEW_LIMIT = 3


def validate_folder_name(name: str) -> str | None:
    """Return an error message for names that must not be used as a scan root."""
    if not name or name in {'.', '..'}:
        return 'invalid folder name'
    if '/' in name or '\\' in name or Path(name).is_absolute():
        return 'invalid folder name'
    if name.startswith('.'):
        return 'hidden folders are not supported'
    return None


def resolve_selected_folders(books_dir: Path, names: list[str]) -> tuple[list[Path], list[str]]:
    """Validate folder names against the books directory and return scan roots."""
    folders: list[Path] = []
    errors: list[str] = []
    books_root = books_dir.resolve()

    for name in names:
        error = validate_folder_name(name)
        if error is not None:
            errors.append(f'{name}: {error}')
            continue

        folder = books_dir / name
        try:
            resolved = folder.resolve()
        except (OSError, RuntimeError) as exc:
            errors.append(f'{name}: {exc}')
            continue

        if not resolved.is_dir():
            errors.append(f'{name}: folder not found')
            continue
        if resolved.parent != books_root:
            errors.append(f'{name}: not a subfolder of the books directory')
            continue

        folders.append(folder)

    return folders, errors


@dataclass
class SyncResult:
    added: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class SyncTask:
    task_id: str
    scope: str = ""
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

    def bump_errors(self, amount: int = 1) -> None:
        with self._lock:
            self.errors += amount

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


def resolve_books_dir(result: SyncResult, on_progress: Callable[[dict], None] | None) -> Path | None:
    books_dir = Path(settings.books_directory) if settings.books_directory else None
    error = None
    if books_dir is None:
        error = "BOOKS_DIRECTORY is not set"
    elif not books_dir.is_dir():
        error = f"BOOKS_DIRECTORY does not exist: {books_dir}"
    if error is not None:
        logger.error(error)
        result.errors.append(error)
        if on_progress:
            on_progress({"done": True, "errors": 1})
        return None
    return books_dir


def format_scope(folders: list[str]) -> str:
    names = sorted(folders, key=str.lower)
    if len(names) <= SCOPE_PREVIEW_LIMIT:
        return ', '.join(names)
    return f"{', '.join(names[:SCOPE_PREVIEW_LIMIT])} and {len(names) - SCOPE_PREVIEW_LIMIT} more"


class SyncService:
    def __init__(self, max_finished_tasks: int = MAX_FINISHED_TASKS):
        self._tasks: dict[str, SyncTask] = {}
        self._max_finished_tasks = max_finished_tasks
        self._lock = Lock()
        self._active: SyncTask | None = None

    def create_task(self, scope: str = 'all folders') -> SyncTask | None:
        """Create a new task, or return None while another sync is still running."""
        with self._lock:
            if self._active is not None and not self._active.done:
                return None
            self.prune()
            task = SyncTask(task_id=uuid.uuid4().hex[:12], scope=scope)
            self._tasks[task.task_id] = task
            self._active = task
            return task

    def get_active_task(self) -> SyncTask | None:
        with self._lock:
            if self._active is not None and not self._active.done:
                return self._active
            return None

    def get_task(self, task_id: str) -> SyncTask | None:
        return self._tasks.get(task_id)

    def prune(self) -> None:
        done_ids = [task_id for task_id, task in list(self._tasks.items()) if task.done]
        for task_id in done_ids[: -self._max_finished_tasks]:
            del self._tasks[task_id]

    def result_message(self, result: SyncResult) -> str:
        if result.errors and not result.added and not result.skipped:
            return f"Sync failed: {result.errors[0]}"
        parts = [f"Synced: {result.added} added, {result.skipped} skipped"]
        if result.errors:
            parts.append(f"{len(result.errors)} errors")
        return ", ".join(parts)

    @staticmethod
    def _resolve_scan_roots(books_dir: Path, folders: list[str] | None, result: SyncResult) -> list[Path] | None:
        if folders is None:
            return [books_dir]
        if not folders:
            result.errors.append('No folders selected')
            return None

        roots, folder_errors = resolve_selected_folders(books_dir, folders)
        if folder_errors:
            for error in folder_errors:
                logger.error("Cannot sync folder: %s", error)
                result.errors.append(error)
            return None
        return roots

    def run(  # noqa: PLR0915
        self,
        folders: list[str] | None = None,
        on_progress: Callable[[dict], None] | None = None,
    ) -> SyncResult:
        result = SyncResult()
        result_lock = Lock()

        books_dir = resolve_books_dir(result, on_progress)
        if books_dir is None:
            return result

        roots = self._resolve_scan_roots(books_dir, folders, result)
        if roots is None:
            if on_progress:
                on_progress({"done": True, "errors": max(len(result.errors), 1)})
            return result

        scope = 'all folders' if folders is None else format_scope(folders)

        logger.info("Sync started, scanning %s", scope)
        scan_result = DirectoryScanner().scan_folders(roots)
        logger.info("Scan complete: %d files found, %d scan errors", len(scan_result.file_paths), len(scan_result.errors))

        for error_path, error_msg in scan_result.errors:
            logger.warning("Scan error: %s — %s", error_path, error_msg)
            result.errors.append(f"{error_path}: {error_msg}")

        total = len(scan_result.file_paths)
        if total == 0:
            logger.info("Sync finished: no files to import")
            if on_progress:
                on_progress({"done": True})
            return result

        logger.info("Importing %d files sequentially", total)

        if on_progress:
            on_progress({"total": total, "processed": 0, "current_file": ""})

        def import_one(idx: int, file_path: Path) -> None:
            logger.info("Importing [%d/%d] %s", idx, total, file_path.name)
            success = False
            try:
                with Session() as session:
                    store = DataStore(session)
                    importer = PathImporter(file_path, set())
                    if not try_claim(importer.checksum):
                        logger.info("Skipping %s: identical file is being imported concurrently", file_path)
                    else:
                        try:
                            with store.transaction():
                                success = importer.process(store)
                        finally:
                            release(importer.checksum)

                with result_lock:
                    if success:
                        result.added += 1
                    else:
                        result.skipped += 1
                    if on_progress:
                        on_progress(
                            {
                                "processed": idx,
                                "added": result.added,
                                "skipped": result.skipped,
                                "errors": len(result.errors),
                                "current_file": file_path.name,
                            }
                        )
            except Exception:
                logger.exception("Error importing %s", file_path)
                with result_lock:
                    result.errors.append(f"{file_path}: import failed")
                    if on_progress:
                        on_progress(
                            {
                                "processed": idx,
                                "added": result.added,
                                "skipped": result.skipped,
                                "errors": len(result.errors),
                                "current_file": file_path.name,
                            }
                        )

        # Imports are sequential on purpose: the pipeline does check-then-insert
        # for shared reference rows (languages, authors, tags), which races under
        # concurrency and loses books with UNIQUE constraint errors. PDFium is not
        # thread-safe either.
        for idx, file_path in enumerate(scan_result.file_paths, start=1):
            import_one(idx, file_path)

        if on_progress:
            on_progress({"done": True})

        logger.info("Sync finished: %d added, %d skipped, %d errors", result.added, result.skipped, len(result.errors))
        return result
