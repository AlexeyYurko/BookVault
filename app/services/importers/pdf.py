import logging
from io import BytesIO
from pathlib import Path
from threading import Lock

import pypdfium2 as pdfium
from PIL import Image
from PyPDF2 import PdfReader

from app.config import settings
from app.services.importers.base import BookImporter, BookMetadata
from app.services.importers.isbn import canonical13, extract_isbns, normalize_isbn
from app.services.importers.text_utils import parse_authors

logger = logging.getLogger(__name__)

MAX_COVER_DIM = 1600

ISBN_SCAN_PAGES = 5

# PDFium is not thread-safe: concurrent calls corrupt its global state and make
# document loading fail ("Data format error") or crash the process. Sync is
# sequential now, but the lock keeps PDFium calls safe if work is parallelized
# again (background tasks, future thread pools).
_PDFIUM_LOCK = Lock()


class PdfImporter(BookImporter):
    FORMAT = 'pdf'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pdf_buffer: BytesIO | None = None

    def _get_pdf_source(self) -> str | BytesIO:
        """Return a path string for local files, BytesIO for uploads."""
        path = getattr(self.file, 'path', None)
        if path is not None:
            return str(path)
        if self._pdf_buffer is None:
            logger.info('Reading PDF into memory: %s', self.file.filename)
            self.file.file.seek(0)
            self._pdf_buffer = BytesIO(self.file.file.read())
        self._pdf_buffer.seek(0)
        return self._pdf_buffer

    def extract_cover(self):
        filename = self._cover_filename
        logger.info('Rendering cover: %s', filename)
        source = self._get_pdf_source()
        with _PDFIUM_LOCK:
            pdf = pdfium.PdfDocument(source)
            try:
                page = pdf.get_page(0)
                bitmap = page.render(scale=300 / 72, optimize_mode=None)
                try:
                    # to_pil() may share the bitmap buffer, so copy before closing it.
                    cover = bitmap.to_pil().copy()
                finally:
                    bitmap.close()
            finally:
                pdf.close()
        path = Path(settings.static_path, settings.cover_images_path, filename)
        if max(cover.width, cover.height) > MAX_COVER_DIM:
            ratio = MAX_COVER_DIM / max(cover.width, cover.height)
            cover = cover.resize((int(cover.width * ratio), int(cover.height * ratio)), Image.LANCZOS)
        logger.info(f"Saving {filename}, width {cover.width}, height {cover.height}")
        cover.save(str(path))
        return filename

    def get_metadata(self):
        logger.info('Parsing PDF metadata: %s', self.file.filename)
        pdf = PdfReader(self._get_pdf_source())
        pdf_info = pdf.metadata
        if pdf_info:
            description = self._resolve_str(pdf_info.get('/Description')) or self._resolve_str(pdf_info.get('/Subject'))
            authors = parse_authors(self._resolve_str(pdf_info.get('/Author')))
            title = self._resolve_str(pdf_info.get('/Title')) or Path(self.file.filename).stem
            publisher = self._resolve_str(pdf_info.get('/Publisher')) or None
            language = self._resolve_str(pdf_info.get('/Language')) or self._resolve_str(pdf_info.get('/Lang')) or None
        else:
            description = ''
            authors = []
            title = Path(self.file.filename).stem
            publisher = None
            language = None

        metadata_isbn = normalize_isbn(self._resolve_str(pdf_info.get('/ISBN'))) if pdf_info else None
        isbns: list[str] = []
        if metadata_isbn:
            isbns.append(metadata_isbn)
        for isbn in self._scan_isbns():
            if canonical13(isbn) not in {canonical13(existing) for existing in isbns}:
                isbns.append(isbn)

        return BookMetadata(
            authors=authors,
            title=title,
            description=description,
            publisher=publisher,
            languages=[language] if language else None,
            published_date=None,
            tags=None,
            isbn=isbns[0] if isbns else None,
            original_isbn=isbns[1] if len(isbns) > 1 else None,
        )

    def _scan_isbns(self):
        logger.info('Scanning first %d pages for ISBN: %s', ISBN_SCAN_PAGES, self.file.filename)
        source = self._get_pdf_source()
        with _PDFIUM_LOCK:
            pdf = pdfium.PdfDocument(source)
            try:
                text = ''
                for index in range(min(len(pdf), ISBN_SCAN_PAGES)):
                    page = pdf.get_page(index)
                    text += page.get_textpage().get_text_bounded()
            finally:
                pdf.close()
        return extract_isbns(text)

    @staticmethod
    def _resolve_str(value) -> str:
        if value is None:
            return ''
        get_object = getattr(value, 'get_object', None)
        if callable(get_object):
            value = get_object()
        if isinstance(value, bytes):
            return value.decode('utf-8', errors='replace')
        return str(value)
