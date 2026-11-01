from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock

from app.db import Session
from app.models import Catalog
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


def resolve_selected_folders(catalog_root: Path, names: list[str]) -> tuple[list[Path], list[str]]:
    """Validate folder names against the catalog root and return scan roots."""
    folders: list[Path] = []
    errors: list[str] = []
    resolved_root = catalog_root.resolve()

    for name in names:
        error = validate_folder_name(name)
        if error is not None:
            errors.append(f'{name}: {error}')
            continue

        folder = catalog_root / name
        try:
            resolved = folder.resolve()
        except (OSError, RuntimeError) as exc:
            errors.append(f'{name}: {exc}')
            continue

        if not resolved.is_dir():
            errors.append(f'{name}: folder not found')
            continue
        if resolved.parent != resolved_root:
            errors.append(f'{name}: not a direct subfolder of the catalog')
            continue

        folders.append(folder)

    return folders, errors


def list_first_level_folders(catalog: Catalog) -> tuple[list[str], str | None]:
    root = Path(catalog.root_path)
    if not root.is_dir():
        return [], f'Catalog directory not found: {root}'
    try:
        folders = [entry.name for entry in root.iterdir() if entry.is_dir() and not entry.name.startswith('.')]
    except OSError as exc:
        return [], f'Could not read catalog directory: {exc}'
    return sorted(folders, key=str.lower), None


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
    current_catalog: str = ""
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
                "current_catalog": self.current_catalog,
                "done": self.done,
                "result_message": self.result_message,
            }


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

    def create_task(self, scope: str = 'all catalogs') -> SyncTask | None:
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
    def _resolve_scan_roots(catalog: Catalog, folders: list[str] | None, result: SyncResult) -> list[Path] | None:
        root = Path(catalog.root_path)
        if folders is None:
            return [root]
        if not folders:
            result.errors.append(f'{catalog.name}: no folders selected')
            return None

        roots, folder_errors = resolve_selected_folders(root, folders)
        if folder_errors:
            for error in folder_errors:
                logger.error("Cannot sync folder: %s", error)
                result.errors.append(f"{catalog.name}: {error}")
            return None
        return roots

    @staticmethod
    def _load_catalogs(catalog_id: int | None) -> list[Catalog]:
        with Session() as session:
            query = session.query(Catalog)
            if catalog_id is None:
                query = query.filter(Catalog.enabled.is_(True))
            else:
                query = query.filter(Catalog.id == catalog_id)
            return list(query.order_by(Catalog.name).all())

    def run(  # noqa: PLR0915
        self,
        catalog_id: int | None = None,
        folders: list[str] | None = None,
        on_progress: Callable[[dict], None] | None = None,
    ) -> SyncResult:
        result = SyncResult()
        result_lock = Lock()
        catalogs = self._load_catalogs(catalog_id)
        if not catalogs:
            result.errors.append('No catalogs selected or enabled for sync')
            if on_progress:
                on_progress({'done': True, 'errors': 1})
            return result

        jobs: list[tuple[Catalog, Path]] = []
        for catalog in catalogs:
            if on_progress:
                on_progress({'current_catalog': catalog.name, 'current_file': ''})
            if not Path(catalog.root_path).is_dir():
                error = f'{catalog.name}: catalog directory is unavailable: {catalog.root_path}'
                logger.error(error)
                result.errors.append(error)
                continue

            roots = self._resolve_scan_roots(catalog, folders if catalog_id is not None else None, result)
            if roots is None:
                continue
            scan_result = DirectoryScanner().scan_folders(roots)
            for error_path, error_msg in scan_result.errors:
                logger.warning("Scan error: %s — %s", error_path, error_msg)
                result.errors.append(f"{catalog.name}: {error_path}: {error_msg}")
            jobs.extend((catalog, file_path) for file_path in scan_result.file_paths)

        total = len(jobs)
        if on_progress:
            on_progress({'total': total, 'processed': 0, 'current_file': ''})

        def import_one(idx: int, catalog: Catalog, file_path: Path) -> None:
            logger.info("Importing [%d/%d] %s from %s", idx, total, file_path.name, catalog.name)
            success = False
            try:
                with Session() as session:
                    store = DataStore(session)
                    importer = PathImporter(file_path, set(), catalog)
                    claim = f"{catalog.id}:{importer.checksum}"
                    if not try_claim(claim):
                        logger.info("Skipping %s: identical file is being imported concurrently", file_path)
                    else:
                        try:
                            with store.transaction():
                                success = importer.process(store)
                        finally:
                            release(claim)

                with result_lock:
                    if success:
                        result.added += 1
                    else:
                        result.skipped += 1
                    if on_progress:
                        on_progress(
                            {
                                'processed': idx,
                                'added': result.added,
                                'skipped': result.skipped,
                                'errors': len(result.errors),
                                'current_file': file_path.name,
                                'current_catalog': catalog.name,
                            }
                        )
            except Exception:
                logger.exception("Error importing %s", file_path)
                with result_lock:
                    result.errors.append(f"{catalog.name}: {file_path}: import failed")
                    if on_progress:
                        on_progress(
                            {
                                'processed': idx,
                                'added': result.added,
                                'skipped': result.skipped,
                                'errors': len(result.errors),
                                'current_file': file_path.name,
                                'current_catalog': catalog.name,
                            }
                        )

        # Imports are sequential on purpose: shared reference rows and PDFium
        # are not safe to process concurrently.
        for idx, (catalog, file_path) in enumerate(jobs, start=1):
            import_one(idx, catalog, file_path)

        if on_progress:
            on_progress({'done': True})
        logger.info("Sync finished: %d added, %d skipped, %d errors", result.added, result.skipped, len(result.errors))
        return result
