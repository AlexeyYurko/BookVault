from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from app.services.importers import BookImporter, DjvuImporter, EpubImporter, PdfImporter

EXT_TO_IMPORTER: dict[str, type[BookImporter]] = {
    '.pdf': PdfImporter,
    '.epub': EpubImporter,
    '.djvu': DjvuImporter,
}


@dataclass
class LocalFileWrapper:
    path: Path
    _file: BinaryIO | None = None

    @property
    def filename(self) -> str:
        return self.path.name

    @property
    def file(self) -> BinaryIO:
        if self._file is None:
            self._file = open(self.path, 'rb')  # noqa: SIM115
        return self._file


class PathImporter:
    def __init__(self, path: Path, tags: set[str]):
        ext = path.suffix.lower()
        importer_cls = EXT_TO_IMPORTER.get(ext)
        if importer_cls is None:
            raise ValueError(f'Unsupported file extension: {ext}')
        self._importer = importer_cls(LocalFileWrapper(path=path), tags, file_path=str(path))

    def process(self, store):
        self._importer.process(store)
