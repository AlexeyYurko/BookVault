import contextlib
import logging
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from ebooklib import epub
from PIL import Image

from app.config import settings
from app.services.importers.base import (
    BookImporter,
    BookMetadata,
)
from app.services.importers.exceptions import ImportBookException


class EpubImporter(BookImporter):
    FORMAT = 'epub'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.book = None

    def get_metadata(self):
        try:
            self.book = self._get_temp_ebook()
        except Exception as e:
            logging.info('Failed to import book')
            raise ImportBookException from e

        title = self.book.get_metadata("DC", 'title')[0][0]

        extended_title = ''
        with contextlib.suppress(IndexError):
            extended_title = self.book.get_metadata("DC", 'extended-title')[1][0]

        title = title if len(title) >= len(extended_title) else extended_title

        authors = self._get_authors()

        publisher = None
        with contextlib.suppress(IndexError):
            publisher = self.book.get_metadata("DC", "publisher")[0][0]

        languages = [language[0] for language in self.book.get_metadata("DC", "language")]

        published_date = None
        with contextlib.suppress(IndexError):
            published_date = self.book.get_metadata("DC", "date")[0][0]

        description = ''
        with contextlib.suppress(IndexError):
            description = self.book.get_metadata("DC", "description")[0][0]

        tags = []

        return BookMetadata(
            authors=authors,
            title=title,
            description=description,
            publisher=publisher,
            languages=languages,
            published_date=published_date,
            tags=tags
        )

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
                path = Path(settings.static_path, settings.cover_images_path, filename)
                cover_image = item.get_content()
                image = Image.open(BytesIO(cover_image))
                if image.mode == 'RGBA':
                    image = image.convert('RGB')
                image.save(str(path))
                break

        return filename

    def _get_authors(self):
        authors = [contributor[0] for contributor in self.book.get_metadata("DC", "creator")]
        cleaned_authors = []
        for author in authors:
            if ' and ' in author:
                and_authors = author.split(' and ')
                cleaned_authors.extend(and_authors)
            else:
                cleaned_authors.append(author)
        authors = cleaned_authors
        return authors

    def _get_temp_ebook(self):
        with NamedTemporaryFile(delete=False) as temp_file:
            while True:
                chunk = self.file.file.read(1024)
                if not chunk:
                    break
                temp_file.write(chunk)
        return epub.read_epub(temp_file.name)
