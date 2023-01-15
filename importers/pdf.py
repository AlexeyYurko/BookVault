import os

import pypdfium2 as pdfium
from PyPDF2 import PdfFileReader

from config import IMAGES_PATH
from importers.base import BookImporter


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
        author = pdf_info.get('/Author', '')
        title = pdf_info.get('/Title', os.path.splitext(self.file.filename)[0])
        return author, title
