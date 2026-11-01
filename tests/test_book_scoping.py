import pytest

from app.models import Author, Tag
from app.services.book_service import BookService


def test_books_are_scoped_by_catalog(store, make_catalog, make_book):
    first = make_catalog("First")
    second = make_catalog("Second")
    book_a = make_book(first, "Same file A", checksum="same", file_path="a.pdf")
    book_b = make_book(second, "Same file B", checksum="same", file_path="a.pdf")

    all_books = store.book_repo.find_books()
    only_first = store.book_repo.find_books(filters={"catalog_id": first.id})

    assert all_books.total == 2
    assert [book.id for book in only_first.books] == [book_a.id]
    assert book_a.id != book_b.id


def test_filter_context_scopes_facets(store, make_catalog, make_book):
    first = make_catalog("First")
    second = make_catalog("Second")
    book_a = make_book(first, "Alpha")
    book_b = make_book(second, "Beta")

    author_a = store.author_repo.create(name="Author A")
    author_b = store.author_repo.create(name="Author B")
    tag_a = store.tag_repo.create(name="tag-a")
    tag_b = store.tag_repo.create(name="tag-b")
    book_a.authors.append(author_a)
    book_a.tags.append(tag_a)
    book_b.authors.append(author_b)
    book_b.tags.append(tag_b)
    store.session.commit()

    context = BookService(store).filter_context(first.id)

    assert [author.name for author in context["authors"]] == ["Author A"]
    assert [tag.name for tag in store.book_repo.get_tags_linked_to_books(first.id)] == ["tag-a"]
    assert context["active_catalog"].id == first.id
    assert {catalog.id for catalog in context["catalogs"]} == {first.id, second.id}
    assert store.session.query(Author).count() == 2
    assert store.session.query(Tag).count() == 2


def test_link_candidates_stay_inside_catalog(store, make_catalog, make_book):
    first = make_catalog("First")
    second = make_catalog("Second")
    book = make_book(first, "Python Crash Course")
    peer = make_book(first, "Python Crash Course 2nd Edition")
    make_book(second, "Python Crash Course")

    candidates = BookService(store).find_link_candidates(book, "Python Crash Course")

    assert [candidate.id for candidate in candidates] == [peer.id]


def test_link_edition_rejects_cross_catalog_pair(store, make_catalog, make_book):
    first = make_catalog("First")
    second = make_catalog("Second")
    book = make_book(first, "Book")
    other = make_book(second, "Book")

    with pytest.raises(ValueError, match="different catalogs"):
        BookService(store).link_edition(book, other)
