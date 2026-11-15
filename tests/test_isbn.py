from app.services.importers.base import BookMetadata
from app.services.importers.context import ImportContext
from app.services.importers.isbn import canonical_isbn
from app.services.importers.steps.extract_metadata import ExtractMetadataStep


class _StubImporter:
    file = "book.epub"
    file_path = "book.epub"

    def __init__(self, metadata: BookMetadata):
        self._metadata = metadata

    def get_metadata(self) -> BookMetadata:
        return self._metadata


def _metadata(**overrides) -> BookMetadata:
    values = {
        "title": "Book",
        "authors": ["Author"],
        "description": None,
        "publisher": None,
        "languages": ["en"],
        "tags": None,
        "published_date": None,
    }
    values.update(overrides)
    return BookMetadata(**values)


def test_canonical_isbn_converts_isbn10_to_isbn13():
    assert canonical_isbn("0-8044-2957-X") == "9780804429573"
    assert canonical_isbn("978-0-8044-2957-3") == "9780804429573"


def test_canonical_isbn_rejects_invalid_values():
    assert canonical_isbn("not-an-isbn") is None
    assert canonical_isbn("978-0-8044-2957-2") is None
    assert canonical_isbn(None) is None


def test_extract_metadata_step_stores_canonical_isbn(store):
    ctx = ImportContext(
        store=store,
        importer=_StubImporter(
            _metadata(isbn="0-8044-2957-X", original_isbn="0-306-40615-2"),
        ),
    )

    result = ExtractMetadataStep().process(ctx)

    assert result is ctx
    assert ctx.metadata.isbn == "9780804429573"
    assert ctx.metadata.original_isbn == "9780306406157"


def test_extract_metadata_step_drops_invalid_isbn(store):
    ctx = ImportContext(store=store, importer=_StubImporter(_metadata(isbn="invalid")))

    ExtractMetadataStep().process(ctx)

    assert ctx.metadata.isbn is None
