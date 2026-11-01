"""add catalogs and catalog-relative book paths

Revision ID: a41c8f2d9e60
Revises: 3f9c1d7a5b2e
Create Date: 2026-10-31 18:00:00.000000

"""
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Union

import sqlalchemy as sa

from alembic import op
from app.config import settings

revision: str = "a41c8f2d9e60"
down_revision: Union[str, Sequence[str], None] = "3f9c1d7a5b2e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "catalogs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("root_path", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("root_path"),
    )
    op.add_column("books", sa.Column("catalog_id", sa.Integer(), nullable=True))

    connection = op.get_bind()
    books = connection.execute(sa.text("SELECT id, file_path FROM books")).mappings().all()
    root_value = settings.books_directory.strip()
    if books and not root_value:
        raise RuntimeError("BOOKS_DIRECTORY must be set to migrate an existing library to catalogs")

    catalog_id = None
    root = None
    if root_value:
        root = Path(root_value).expanduser().resolve()
        connection.execute(
            sa.text("INSERT INTO catalogs (name, root_path, kind, enabled) VALUES (:name, :root, 'book', 1)"),
            {"name": "Books", "root": str(root)},
        )
        catalog_id = connection.execute(
            sa.text("SELECT id FROM catalogs WHERE root_path = :root"),
            {"root": str(root)},
        ).scalar_one()
        connection.execute(sa.text("UPDATE books SET catalog_id = :catalog_id"), {"catalog_id": catalog_id})

    for book in books:
        file_path = book["file_path"]
        if not file_path:
            continue
        path = Path(file_path)
        if path.is_absolute():
            try:
                relative = Path(os.path.abspath(file_path)).relative_to(root)
            except ValueError:
                raise RuntimeError(
                    f"Cannot migrate book {book['id']}: file path is outside BOOKS_DIRECTORY: {file_path}"
                ) from None
        else:
            relative = path
        if ".." in relative.parts:
            raise RuntimeError(f"Cannot migrate book {book['id']}: unsafe relative path: {file_path}")
        connection.execute(
            sa.text("UPDATE books SET file_path = :file_path WHERE id = :book_id"),
            {"file_path": relative.as_posix(), "book_id": book["id"]},
        )

    with op.batch_alter_table("books") as batch_op:
        batch_op.alter_column("catalog_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key("book_catalog_fk", "catalogs", ["catalog_id"], ["id"])
    op.create_index("ix_books_catalog_id", "books", ["catalog_id"])
    op.create_index("ix_books_catalog_checksum", "books", ["catalog_id", "checksum"])


def downgrade() -> None:
    connection = op.get_bind()
    books = connection.execute(
        sa.text(
            "SELECT b.id, b.file_path, c.root_path FROM books b JOIN catalogs c ON c.id = b.catalog_id"
        )
    ).mappings().all()
    for book in books:
        file_path = book["file_path"]
        if file_path and not Path(file_path).is_absolute():
            connection.execute(
                sa.text("UPDATE books SET file_path = :file_path WHERE id = :book_id"),
                {"file_path": str(Path(book["root_path"]) / file_path), "book_id": book["id"]},
            )

    op.drop_index("ix_books_catalog_checksum", table_name="books")
    op.drop_index("ix_books_catalog_id", table_name="books")
    with op.batch_alter_table("books") as batch_op:
        batch_op.drop_constraint("book_catalog_fk", type_="foreignkey")
        batch_op.drop_column("catalog_id")
    op.drop_table("catalogs")
