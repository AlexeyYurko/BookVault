from pathlib import Path

from app.db import Session
from app.models import Book, Catalog
from app.services.sync_service import SyncService, resolve_selected_folders


def test_sync_all_only_loads_enabled_catalogs(make_catalog):
    make_catalog("Enabled")
    make_catalog("Disabled", enabled=False)

    catalogs = SyncService._load_catalogs(None)

    assert [catalog.name for catalog in catalogs] == ["Enabled"]


def test_offline_catalog_keeps_its_books(store, make_catalog, make_book):
    catalog = make_catalog()
    make_book(catalog, "Offline book", file_path="book.pdf")
    Path(catalog.root_path).rmdir()

    result = SyncService().run(catalog_id=catalog.id)

    assert result.errors
    assert "unavailable" in result.errors[0]
    store.session.expire_all()
    assert store.session.query(Book).count() == 1


def test_missing_selected_folder_is_reported(tmp_path):
    root = tmp_path / "books"
    root.mkdir()

    folders, errors = resolve_selected_folders(root, ["missing"])

    assert folders == []
    assert errors == ["missing: folder not found"]


def test_nested_folder_is_rejected(tmp_path):
    root = tmp_path / "books"
    (root / "sub" / "deeper").mkdir(parents=True)

    folders, errors = resolve_selected_folders(root, ["sub/deeper"])

    assert folders == []
    assert errors == ["sub/deeper: invalid folder name"]


def test_symlink_outside_catalog_is_rejected(tmp_path):
    root = tmp_path / "books"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "link").symlink_to(outside, target_is_directory=True)

    folders, errors = resolve_selected_folders(root, ["link"])

    assert folders == []
    assert errors == ["link: not a direct subfolder of the catalog"]


def test_valid_subfolder_is_selected(tmp_path):
    root = tmp_path / "books"
    (root / "sub").mkdir(parents=True)

    folders, errors = resolve_selected_folders(root, ["sub"])

    assert folders == [root / "sub"]
    assert errors == []


def test_catalog_lookup_by_id_includes_disabled_catalog(make_catalog):
    catalog = make_catalog("Disabled", enabled=False)

    assert [item.id for item in SyncService._load_catalogs(catalog.id)] == [catalog.id]
    with Session() as session:
        assert session.query(Catalog).count() == 1
