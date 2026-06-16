import logging
from io import BytesIO
from pathlib import Path

import pypdfium2 as pdfium
from PyPDF2 import PdfReader

from app.config import settings
from app.services.importers.base import BookImporter, BookMetadata

logger = logging.getLogger(__name__)


class PdfImporter(BookImporter):
    FORMAT = 'pdf'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pdf_buffer: BytesIO | None = None

    def _get_pdf_buffer(self) -> BytesIO:
        if self._pdf_buffer is None:
            self.file.file.seek(0)
            self._pdf_buffer = BytesIO(self.file.file.read())
        self._pdf_buffer.seek(0)
        return self._pdf_buffer

    def extract_cover(self):
        filename = self._cover_filename
        pdf = pdfium.PdfDocument(self._get_pdf_buffer())
        page = pdf.get_page(0)
        cover = page.render(scale=300 / 72, optimize_mode=None).to_pil()
        path = Path(settings.static_path, settings.cover_images_path, filename)
        logger.info(f"Saving {filename}, width {cover.width}, height {cover.height}")
        cover.save(str(path))
        return filename

    def get_metadata(self):
        pdf = PdfReader(self._get_pdf_buffer())
        pdf_info = pdf.metadata
        if pdf_info:
            description = pdf_info.get('/Description', pdf_info.get('/Subject')) or ''
            authors = str(pdf_info.get('/Author', '')).split(',')
            title = pdf_info.get('/Title') or self.file.filename.split('.')[0]
        else:
            description = ''
            authors = ''
            title = self.file.filename.split('.')[0]
        return BookMetadata(
            authors=authors,
            title=title,
            description=description,
            publisher=None,
            languages=None,
            published_date=None,
            tags=None,
        )
