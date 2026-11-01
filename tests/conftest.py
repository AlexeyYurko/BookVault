from __future__ import annotations

import os
import tempfile
from pathlib import Path

_TEST_ROOT = Path(tempfile.mkdtemp(prefix="bookvault-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_ROOT / 'bookvault.db'}"
os.environ["BOOKS_DIRECTORY"] = str(_TEST_ROOT / "books")
os.environ["TEMP_DIR"] = str(_TEST_ROOT / "tmp")

import pytest  # noqa: E402

import app.models  # noqa: E402, F401
from app.db import Session  # noqa: E402
from app.db.base import Base, engine  # noqa: E402
from app.models import Book, Catalog, Language  # noqa: E402
from app.repositories.data_store import DataStore  # noqa: E402


@pytest.fixture(autouse=True)
def database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Session.remove()


@pytest.fixture
def store():
    with Session() as session:
        yield DataStore(session)


@pytest.fixture
def make_catalog(store):
    def create(name: str = "Books", root: Path | None = None, *, kind: str = "book", enabled: bool = True) -> Catalog:
        path = root or Path(tempfile.mkdtemp(dir=_TEST_ROOT))
        catalog = store.catalog_repo.create(
            name=name,
            root_path=str(path),
            kind=kind,
            enabled=enabled,
        )
        store.session.commit()
        return catalog

    return create


@pytest.fixture
def make_book(store):
    def create(
        catalog: Catalog,
        title: str = "Book",
        *,
        checksum: str | None = None,
        file_path: str | None = None,
        language_code: str = "en",
    ) -> Book:
        if store.session.get(Language, language_code) is None:
            store.session.add(Language(code=language_code, name=language_code.upper()))
            store.session.flush()
        book = store.book_repo.create(
            title=title,
            language_code=language_code,
            catalog_id=catalog.id,
            checksum=checksum,
            file_path=file_path,
        )
        store.session.commit()
        return book

    return create
