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

    def _read_pdf_file(self, reader_type):
        if reader_type == 'pdfium':
            return pdfium.PdfDocument(self._get_file_attribute())
        elif reader_type == 'pypdf':
            return PdfFileReader(self._get_file_attribute())

    def _get_file_attribute(self):
        return self.file.file._file

    def extract_cover(self):
        filename = self._cover_filename
        pdf = self._read_pdf_file('pdfium')
        page = pdf.get_page(0)
        cover = page.render_topil(scale=2, optimise_mode=pdfium.OptimiseMode.NONE)
        path = os.path.join(IMAGES_PATH, filename)
        print(f"Saving {filename}, width {cover.width}, height {cover.height}")
        cover.save(path)
        return filename

    def get_metadata(self):
        pdf = self._read_pdf_file('pypdf')
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
            tags=None
        )