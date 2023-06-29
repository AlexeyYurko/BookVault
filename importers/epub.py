import os
from io import BytesIO
from tempfile import NamedTemporaryFile

from ebooklib import epub
from PIL import Image

from config import IMAGES_PATH
from importers.base import BookImporter


class EpubImporter(BookImporter):
    FORMAT = 'epub'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.book = None

    def get_metadata(self):
        self.book = self._get_temp_ebook()

        title = self.book.get_metadata("DC", 'title')[0][0]

        extended_title = ''
        try:
            extended_title = self.book.get_metadata("DC", 'extended-title')[1][0]
        except IndexError:
            pass
        title = title if len(title) >= len(extended_title) else extended_title

        authors = [contributor[0] for contributor in self.book.get_metadata("DC", "creator")]

        description = None
        try:
            description = self.book.get_metadata("DC", "description")[0][0]
        except IndexError:
            pass

        return authors, title, description

    def _get_temp_ebook(self):
        with NamedTemporaryFile(delete=False) as temp_file:
            while True:
                chunk = self.file.file.read(1024)
                if not chunk:
                    break
                temp_file.write(chunk)
        return epub.read_epub(temp_file.name)

    def extract_cover(self):
        filename = None

        try:
            cover_item_filename = self.book.get_metadata('OPF', 'cover')[0][1]['content']
        except (IndexError, KeyError):
            cover_item_filename = ''

        for item in self.book.get_items():
            if (
                    'cover' in item.file_name.lower() or 'cover' in item.id or cover_item_filename == item.file_name) and item.media_type in [
                'image/jpeg',
                'image/png',
            ]:
                filename = self._cover_filename
                path = os.path.join(IMAGES_PATH, filename)
                cover_image = item.get_content()
                image = Image.open(BytesIO(cover_image))
                if image.mode == 'RGBA':
                    image = image.convert('RGB')
                image.save(path)
                break

        return filename
