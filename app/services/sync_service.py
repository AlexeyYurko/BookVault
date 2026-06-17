from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from app.config import settings
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
    def run(self, store: DataStore) -> SyncResult:
        result = SyncResult()

        books_dir = Path(settings.books_directory)
        if not books_dir or not books_dir.is_dir():
            logger.error('BOOKS_DIRECTORY is not set or does not exist: %s', books_dir)
            result.errors.append('BOOKS_DIRECTORY is not set or does not exist')
            return result

        logger.info('Sync started, scanning %s', books_dir)
        scan_result = DirectoryScanner().scan(books_dir)
        logger.info('Scan complete: %d files found, %d scan errors',
                     len(scan_result.file_paths), len(scan_result.errors))

        for error_path, error_msg in scan_result.errors:
            logger.warning('Scan error: %s — %s', error_path, error_msg)
            result.errors.append(f'{error_path}: {error_msg}')

        total = len(scan_result.file_paths)
        for idx, file_path in enumerate(scan_result.file_paths, start=1):
            logger.info('Importing [%d/%d] %s', idx, total, file_path.name)
            try:
                importer = PathImporter(file_path, set())
                with store.transaction():
                    if importer.process(store):
                        result.added += 1
                    else:
                        result.skipped += 1
            except Exception:
                logger.exception('Error importing %s', file_path)
                result.errors.append(f'{file_path}: import failed')

        logger.info('Sync finished: %d added, %d skipped, %d errors',
                     result.added, result.skipped, len(result.errors))
        return result
