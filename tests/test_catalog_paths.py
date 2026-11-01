from pathlib import Path

import pytest

from app.models import Book, Catalog
from app.services.catalog_paths import (
    PathOutsideCatalogError,
    relative_file_path,
    resolve_book_file,
)


def catalog_at(root: Path) -> Catalog:
    return Catalog(name="Books", root_path=str(root), kind="book", enabled=True)


def dir_with_file(root: Path, relative: str = "Author/Book.pdf") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"content")
    return path


def test_relative_file_path_uses_posix_separators(tmp_path):
    catalog = catalog_at(tmp_path)
    path = dir_with_file(tmp_path, "Author/Book.pdf")

    assert relative_file_path(catalog, path) == "Author/Book.pdf"


def test_relative_file_path_rejects_file_outside_catalog(tmp_path):
    catalog_root = tmp_path / "catalog"
    catalog_root.mkdir()
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(b"content")

    with pytest.raises(PathOutsideCatalogError):
        relative_file_path(catalog_at(catalog_root), outside)


def test_resolve_book_file_resolves_relative_path(tmp_path):
    catalog = catalog_at(tmp_path)
    expected = dir_with_file(tmp_path)
    book = Book(title="Book", file_path="Author/Book.pdf", catalog=catalog, language_code="en")

    assert resolve_book_file(book) == expected.resolve()


def test_resolve_book_file_rejects_traversal(tmp_path):
    catalog = catalog_at(tmp_path)
    book = Book(title="Book", file_path="../outside.pdf", catalog=catalog, language_code="en")

    with pytest.raises(PathOutsideCatalogError):
        resolve_book_file(book)


def test_resolve_book_file_rejects_absolute_path(tmp_path):
    catalog = catalog_at(tmp_path)
    book = Book(title="Book", file_path=str(tmp_path / "Book.pdf"), catalog=catalog, language_code="en")

    with pytest.raises(PathOutsideCatalogError):
        resolve_book_file(book)


def test_resolve_book_file_rejects_symlink_escape(tmp_path):
    catalog_root = tmp_path / "catalog"
    catalog_root.mkdir()
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(b"content")
    (catalog_root / "Book.pdf").symlink_to(outside)
    book = Book(title="Book", file_path="Book.pdf", catalog=catalog_at(catalog_root), language_code="en")

    with pytest.raises(PathOutsideCatalogError):
        resolve_book_file(book)
