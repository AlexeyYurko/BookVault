from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

MIME_TO_EXT: dict[str, str] = {
    'application/pdf': '.pdf',
    'application/epub+zip': '.epub',
    'application/djvu': '.djvu',
}
SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(MIME_TO_EXT.values())


@dataclass
class ScanResult:
    file_paths: list[Path] = field(default_factory=list)
    errors: list[tuple[Path, str]] = field(default_factory=list)


class DirectoryScanner:
    def scan(self, root: Path) -> ScanResult:
        return self.scan_folders([root])

    def scan_folders(self, folders: Iterable[Path]) -> ScanResult:
        """Scan several roots, deduplicating files that resolve to the same path."""
        result = ScanResult()
        seen: set[Path] = set()

        for folder in folders:
            self._scan_one(folder, result, seen)

        return result

    def _scan_one(self, root: Path, result: ScanResult, seen: set[Path]) -> None:
        if not root.is_dir():
            result.errors.append((root, 'Not a directory'))
            return

        for path in root.rglob('*'):
            # cheap extension check first - filters most of the tree (no syscall)
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            # skip files inside hidden directories (prefixed with .)
            if any(part.startswith('.') for part in path.relative_to(root).parts[:-1]):
                continue

            # stat only for candidates that passed cheap checks
            if not path.is_file():
                continue

            # dedup via resolved path (catches symlink duplicates) - only on kept files
            try:
                resolved = path.resolve()
            except (OSError, RuntimeError) as exc:
                result.errors.append((path, str(exc)))
                continue
            if resolved in seen:
                continue
            seen.add(resolved)

            result.file_paths.append(path)
