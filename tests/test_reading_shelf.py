from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app


def _shelf_html(html: str) -> str:
    start = html.index('id="reading-shelf"')
    return html[start:html.index("</details>", start)]


def _mark_read(store, book, *, minutes_ago: int, percent: float = 42.0) -> None:
    book.reading_percent = percent
    book.reading_updated_at = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    store.session.commit()


def test_homepage_shows_ten_most_recently_read_books(make_catalog, make_book, store):
    catalog = make_catalog("Books")
    for index in range(12):
        book = make_book(catalog, f"Read Book {index:02d}")
        _mark_read(store, book, minutes_ago=index, percent=float(index + 1))
    make_book(catalog, "Unread Book")

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    shelf = _shelf_html(response.text)
    assert '<details id="reading-shelf" open' in response.text
    assert "<summary" in shelf
    assert "shelf-chevron" in shelf
    assert shelf.count("group/cover") == 10
    assert "group-hover/cover:scale-105" in shelf
    assert "Continue reading" in shelf
    assert "12 books in progress" in shelf
    assert "Show all 12" in shelf
    assert shelf.index("<summary") < shelf.index("Show all 12") < shelf.index("</summary>")
    assert "Read Book 00" in shelf
    assert "Read Book 09" in shelf
    assert "Read Book 10" not in shelf
    assert "Read Book 11" not in shelf
    assert "Unread Book" not in shelf
    positions = [shelf.index(f"Read Book {index:02d}") for index in range(10)]
    assert positions == sorted(positions)


def test_reading_shelf_can_expand_to_every_marked_book(make_catalog, make_book, store):
    catalog = make_catalog("Books")
    for index in range(12):
        book = make_book(catalog, f"Read Book {index:02d}")
        _mark_read(store, book, minutes_ago=index, percent=float(index + 1))
    make_book(catalog, "Unread Book")

    with TestClient(app) as client:
        response = client.get("/reading-shelf", params={"all": 1})

    assert response.status_code == 200
    assert response.text.count('id="reading-shelf"') == 1
    assert "Show less" in response.text
    assert "Read Book 00" in response.text
    assert "Read Book 11" in response.text
    assert "Unread Book" not in response.text


def test_reading_shelf_is_only_part_of_the_homepage(make_catalog, make_book, store):
    catalog = make_catalog("Books")
    book = make_book(catalog, "Read Book")
    _mark_read(store, book, minutes_ago=0)

    with TestClient(app) as client:
        search = client.get("/books/search", params={"query": "Read"})

    assert search.status_code == 200
    assert "Continue reading" not in search.text


def test_reading_shelf_hidden_without_marked_books(make_catalog, make_book):
    catalog = make_catalog("Books")
    make_book(catalog, "Unread Book")

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert 'id="reading-shelf"' not in response.text
