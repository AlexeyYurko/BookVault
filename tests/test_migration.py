import os
import sqlite3
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_REVISION = "3f9c1d7a5b2e"


def run_alembic(db_path: Path, books_dir: Path, *args: str) -> None:
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{db_path}",
        "BOOKS_DIRECTORY": str(books_dir),
    }
    result = subprocess.run(
        [str(Path(sys.executable).parent / "alembic"), *args],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_migration_moves_existing_library_into_a_catalog(tmp_path):
    db_path = tmp_path / "bookvault.db"
    books_dir = tmp_path / "books"
    book_path = books_dir / "Author" / "Book.pdf"
    book_path.parent.mkdir(parents=True)
    book_path.write_bytes(b"content")

    run_alembic(db_path, books_dir, "upgrade", PREVIOUS_REVISION)

    with sqlite3.connect(db_path) as connection:
        connection.execute("INSERT INTO languages (code, name) VALUES ('en', 'English')")
        connection.execute(
            "INSERT INTO books (title, language_code, file_path) VALUES (?, ?, ?)",
            ("Book", "en", str(book_path)),
        )
        connection.commit()

    run_alembic(db_path, books_dir, "upgrade", "head")

    with sqlite3.connect(db_path) as connection:
        catalogs = connection.execute("SELECT id, name, root_path, kind, enabled FROM catalogs").fetchall()
        book = connection.execute("SELECT file_path, catalog_id FROM books").fetchone()

    assert catalogs == [(1, "Books", str(books_dir.resolve()), "book", 1)]
    assert book == ("Author/Book.pdf", 1)

    run_alembic(db_path, books_dir, "downgrade", PREVIOUS_REVISION)

    with sqlite3.connect(db_path) as connection:
        restored = connection.execute("SELECT file_path FROM books").fetchone()
        catalog_table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'catalogs'"
        ).fetchone()

    assert restored == (str(book_path),)
    assert catalog_table is None
