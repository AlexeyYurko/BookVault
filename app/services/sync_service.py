from __future__ import annotations

import logging
import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock

from app.config import settings
from app.db import Session
from app.repositories.data_store import DataStore
from app.services.directory_scanner import DirectoryScanner
from app.services.importers.filesystem import PathImporter

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    added: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


class SyncService:
    def __init__(
        self,
        store: DataStore,
    ):
        self.store = store

    def run(
        self,
        max_workers: int | None = None,
        on_progress: Callable[[dict], None] | None = None,
    ) -> SyncResult:
        result = SyncResult()
        result_lock = Lock()

        books_dir = Path(settings.books_directory)
        if not books_dir or not books_dir.is_dir():
            logger.error("BOOKS_DIRECTORY is not set or does not exist: %s", books_dir)
            result.errors.append("BOOKS_DIRECTORY is not set or does not exist")
            if on_progress:
                on_progress({"done": True, "errors": 1})
            return result

        logger.info("Sync started, scanning %s", books_dir)
        scan_result = DirectoryScanner().scan(books_dir)
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

        workers = max_workers or min(32, (os.cpu_count() or 1) + 2)
        logger.info("Importing %d files with up to %d workers", total, workers)

        if on_progress:
            on_progress({"total": total, "processed": 0, "current_file": ""})

        def import_one(idx: int, file_path: Path) -> None:
            logger.info("Importing [%d/%d] %s", idx, total, file_path.name)
            try:
                with Session() as session:
                    store = DataStore(session)
                    importer = PathImporter(file_path, set())
                    with store.transaction():
                        success = importer.process(store)

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

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(import_one, idx, file_path)
                for idx, file_path in enumerate(scan_result.file_paths, start=1)
            ]
            for future in futures:
                future.result()

        if on_progress:
            on_progress({"done": True})

        logger.info("Sync finished: %d added, %d skipped, %d errors", result.added, result.skipped, len(result.errors))
        return result
