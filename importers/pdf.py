import os

import pypdfium2 as pdfium
from PyPDF2 import PdfFileReader

from config import IMAGES_PATH
from importers.base import (
    BookImporter,
    BookMetadata,
)


class PdfImporter(BookImporter):
    FORMAT = 'pdf'

    def extract_cover(self):
        filename = self._cover_filename
        pdf = pdfium.PdfDocument(self.file.file._file)
        page = pdf.get_page(0)
        cover = page.render_topil(scale=2, optimise_mode=pdfium.OptimiseMode.NONE)
        path = os.path.join(IMAGES_PATH, filename)
        print(f"Saving {filename}, width {cover.width}, height {cover.height}")
        cover.save(path)
        return filename

    def get_metadata(self):
        pdf = PdfFileReader(self.file.file)
        pdf_info = pdf.metadata
        description = pdf_info.get('/Description', pdf_info.get('/Subject')) or ''
        authors = str(pdf_info.get('/Author', '')).split(',')
        title = pdf_info.get('/Title') or os.path.splitext(self.file.filename)[0]
        return BookMetadata(
            authors=authors,
            title=title,
            description=description,
            publisher=None,
            languages=None,
            published_date=None,
            tags=None
        )