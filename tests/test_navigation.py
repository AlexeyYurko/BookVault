from urllib.parse import urlsplit

from fastapi.testclient import TestClient

from app.main import app


def test_catalog_links_to_books_without_return_urls(make_catalog, make_book):
    catalog = make_catalog("Books")
    book = make_book(catalog, "Alpha Book", file_path="alpha.pdf")

    with TestClient(app) as client:
        response = client.get("/", params={"query": "Alpha", "page": 1})

    assert response.status_code == 200
    assert f'href="http://testserver/books/{book.id}"' in response.text
    assert f'href="http://testserver/books/{book.id}/read"' in response.text
    assert "?next=" not in response.text
    assert 'src="http://testserver/static/js/navigation.js"' in response.text


def test_book_pages_use_canonical_navigation_links(make_catalog, make_book):
    catalog = make_catalog("Books")
    book = make_book(catalog, "Alpha Book", file_path="alpha.pdf")

    with TestClient(app) as client:
        book_response = client.get(f"/books/{book.id}")
        detail_response = client.get(f"/books/{book.id}/detail")
        reader_response = client.get(f"/books/{book.id}/read")
        edit_response = client.get(f"/books/{book.id}/edit")

    for response in (book_response, detail_response, reader_response, edit_response):
        assert response.status_code == 200
        assert "?next=" not in response.text

    assert 'href="http://testserver/" data-library-back' in book_response.text
    assert f'href="http://testserver/books/{book.id}/read"' in book_response.text
    assert f'href="http://testserver/books/{book.id}/edit"' in book_response.text
    assert f'href="http://testserver/books/{book.id}"' in detail_response.text
    assert f'href="http://testserver/books/{book.id}" data-history-back' in reader_response.text
    assert 'name="next"' not in edit_response.text
    assert 'name="back_url"' not in edit_response.text
    assert edit_response.text.count(f'href="http://testserver/books/{book.id}"') >= 2


def test_saving_book_redirects_to_clean_book_url(make_catalog, make_book):
    catalog = make_catalog("Books")
    book = make_book(catalog, "Alpha Book")

    with TestClient(app) as client:
        response = client.post(
            f"/books/{book.id}/edit",
            data={
                "title": "Updated Book",
                "language_code": "en",
                "next": "/?page=4",
                "back_url": f"/books/{book.id}?next=/?page=4",
            },
            follow_redirects=False,
        )

    assert response.status_code == 303
    location = urlsplit(response.headers["location"])
    assert location.path == f"/books/{book.id}"
    assert not location.query
