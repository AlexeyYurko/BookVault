from pathlib import Path

import pytest

from app.services.catalog_service import CatalogService


def test_rejects_duplicate_and_nested_paths(store, tmp_path):
    service = CatalogService(store)
    root = tmp_path / "books"
    nested = root / "nested"
    nested.mkdir(parents=True)

    with service.transaction():
        service.create(name="Books", root_path=str(root), kind="book", enabled=True)

    with pytest.raises(ValueError, match="already used"):
        service.create(name="Duplicate", root_path=str(root), kind="book", enabled=True)

    with pytest.raises(ValueError, match="must not overlap"):
        service.create(name="Nested", root_path=str(nested), kind="book", enabled=True)


def test_rejects_parent_of_existing_catalog(store, tmp_path):
    service = CatalogService(store)
    nested = tmp_path / "books" / "nested"
    nested.mkdir(parents=True)

    with service.transaction():
        service.create(name="Nested", root_path=str(nested), kind="book", enabled=True)

    with pytest.raises(ValueError, match="must not overlap"):
        service.create(name="Parent", root_path=str(tmp_path / "books"), kind="book", enabled=True)


def test_rejects_symlinked_catalog_root(store, tmp_path):
    service = CatalogService(store)
    real = tmp_path / "books"
    real.mkdir()
    link = tmp_path / "books-link"
    link.symlink_to(real, target_is_directory=True)

    with service.transaction():
        service.create(name="Books", root_path=str(real), kind="book", enabled=True)

    with pytest.raises(ValueError, match="already used"):
        service.create(name="Link", root_path=str(link), kind="book", enabled=True)


def test_rejects_relative_and_missing_paths(store, tmp_path):
    service = CatalogService(store)

    with pytest.raises(ValueError, match="absolute"):
        service.create(name="Relative", root_path="books", kind="book", enabled=True)

    with pytest.raises(ValueError, match="does not exist"):
        service.create(name="Missing", root_path=str(tmp_path / "missing"), kind="book", enabled=True)


def test_offline_catalog_can_be_edited_without_changing_root(store, tmp_path):
    service = CatalogService(store)
    root = tmp_path / "books"
    root.mkdir()

    with service.transaction():
        catalog = service.create(name="Books", root_path=str(root), kind="book", enabled=True)
    catalog_id = catalog.id
    root.rmdir()

    with service.transaction():
        catalog = service.get(catalog_id)
        updated = service.update(catalog, name="Offline", root_path=catalog.root_path, kind="book", enabled=False)

    assert updated.name == "Offline"
    assert updated.enabled is False


def test_non_empty_catalog_cannot_be_deleted(store, make_catalog, make_book):
    catalog = make_catalog()
    make_book(catalog)
    service = CatalogService(store)

    with pytest.raises(ValueError, match="empty catalog"), service.transaction():
        service.delete(service.get(catalog.id))


def test_empty_catalog_can_be_deleted(store, make_catalog):
    catalog = make_catalog()
    service = CatalogService(store)

    with service.transaction():
        service.delete(service.get(catalog.id))

    assert service.get(catalog.id) is None


def test_root_path_is_stored_resolved(store, tmp_path):
    service = CatalogService(store)
    root = tmp_path / "books"
    root.mkdir()
    path_with_dot = root / "."

    with service.transaction():
        catalog = service.create(name="Books", root_path=str(path_with_dot), kind="book", enabled=True)

    assert Path(catalog.root_path) == root.resolve()
