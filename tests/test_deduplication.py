from app.services.importers.context import ImportContext
from app.services.importers.steps.deduplication import DeduplicationStep


class FakeImporter:
    def __init__(self, catalog, checksum: str, file_path: str):
        self.catalog = catalog
        self.file_path = file_path
        self._checksum = checksum

    def _calculate_checksum(self) -> str:
        return self._checksum


def test_dedup_is_scoped_to_catalog(store, make_catalog, make_book):
    first = make_catalog("First")
    second = make_catalog("Second")
    existing = make_book(first, "Original", checksum="same", file_path="old.pdf")
    ctx = ImportContext(store=store, importer=FakeImporter(second, "same", "old.pdf"))

    result = DeduplicationStep().process(ctx)

    assert result is ctx
    assert ctx.is_new is True
    assert ctx.existing_book is None
    assert existing.id is not None


def test_dedup_finds_existing_book_in_same_catalog(store, make_catalog, make_book):
    catalog = make_catalog()
    existing = make_book(catalog, "Original", checksum="same", file_path="old.pdf")
    ctx = ImportContext(store=store, importer=FakeImporter(catalog, "same", "old.pdf"))

    result = DeduplicationStep().process(ctx)

    assert result is None
    assert ctx.is_new is False
    assert ctx.existing_book is existing


def test_dedup_updates_missing_path_in_same_catalog(store, make_catalog, make_book):
    catalog = make_catalog()
    existing = make_book(catalog, "Original", checksum="same", file_path="missing.pdf")
    ctx = ImportContext(store=store, importer=FakeImporter(catalog, "same", "new.pdf"))

    DeduplicationStep().process(ctx)

    assert existing.file_path == "new.pdf"
