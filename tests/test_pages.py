from fastapi.testclient import TestClient

from app.main import app
from app.models import Book


def test_homepage_filters_books_by_catalog(make_catalog, make_book):
    first = make_catalog("First Catalog")
    second = make_catalog("Second Catalog")
    make_book(first, "Alpha Book")
    make_book(second, "Beta Book")

    with TestClient(app) as client:
        response = client.get("/", params={"catalog_id": first.id})

    assert response.status_code == 200
    assert "Alpha Book" in response.text
    assert "Beta Book" not in response.text
    assert "catalog: First Catalog" in response.text


def test_unknown_catalog_filter_is_ignored(make_catalog, make_book):
    catalog = make_catalog("Books")
    make_book(catalog, "Visible Book")

    with TestClient(app) as client:
        response = client.get("/", params={"catalog_id": 999999})

    assert response.status_code == 200
    assert "Visible Book" in response.text


def test_book_catalogs_hide_issue_sort_controls(make_catalog, make_book):
    catalog = make_catalog("Books")
    make_book(catalog, "Plain Book")

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "sort_by=issue_year" not in response.text


def test_magazine_catalogs_get_issue_sort_controls(make_catalog, make_book, store):
    catalog = make_catalog("Magazines", kind="magazine")
    book = make_book(catalog, "Retro Gamer")
    book.publication_name = "Retro Gamer"
    book.issue_number = "123"
    book.issue_year = 2024
    book.issue_month = 5
    store.session.commit()

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "sort_by=issue_year" in response.text
    assert "sort_by=publication_name" in response.text


def test_book_edition_is_shown_in_the_catalog(make_catalog, make_book, store):
    catalog = make_catalog("Books")
    book = make_book(catalog, "Design Patterns")
    book.edition = "2nd Edition"
    store.session.commit()

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "2nd Edition" in response.text


def test_catalog_settings_page_lists_catalogs(make_catalog):
    make_catalog("My Books")

    with TestClient(app) as client:
        response = client.get("/settings/catalogs")

    assert response.status_code == 200
    assert "My Books" in response.text


def test_seed_endpoint_assigns_a_catalog(store):
    with TestClient(app) as client:
        response = client.get("/db/seed_db")

    assert response.status_code == 200
    store.session.expire_all()
    assert all(book.catalog_id for book in store.session.query(Book).all())
