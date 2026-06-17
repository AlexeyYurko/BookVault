from __future__ import annotations

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
        if not root.is_dir():
            return ScanResult(errors=[(root, 'Not a directory')])

        result = ScanResult()
        seen: set[Path] = set()

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

        return result
