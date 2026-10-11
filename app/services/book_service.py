from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models import BookSeries
from app.models.language import Language
from app.services.importers import DjvuImporter, EpubImporter, PdfImporter
from app.services.importers.dedup_guard import release, try_claim
from app.services.importers.isbn import canonical13, normalize_isbn
from app.services.metadata_lookup import BookMetadata, lookup_book
from app.services.metadata_resync import (
    mark_fields_updated,
    reset_field_protection,
    resync_book_metadata,
)

if TYPE_CHECKING:
    from app.models import Author, Book, Publisher, Tag
    from app.repositories.data_store import DataStore

logger = logging.getLogger(__name__)

ALLOWED_TYPES = {
    "application/pdf": PdfImporter,
    "application/epub+zip": EpubImporter,
    "application/djvu": DjvuImporter,
}


@dataclass
class ImportedFile:
    file: object
    filename: str
    content_type: str


@dataclass
class EditBookDTO:
    title: str
    author_names: str
    publisher_name: str
    series_name: str
    language_code: str
    edition: str
    isbn: str
    original_isbn: str
    format: str
    amazon_url: str
    goodreads_url: str
    tags_str: str
    description: str


@dataclass
class EditValidation:
    errors: list[str] = field(default_factory=list)
    isbn: str | None = None
    original_isbn: str | None = None
    language: Language | None = None


@dataclass
class LookupResult:
    values: dict
    error: str | None = None
    notice: dict | None = None


class BookService:
    def __init__(self, store: DataStore):
        self.store = store

    def transaction(self):
        return self.store.transaction()

    def get_book_by_id(self, book_id: int) -> Book | None:
        return self.store.book_repo.get_book_by_id(book_id)

    def delete_books(self, book_ids: list[int]) -> None:
        self.store.book_repo.delete_books(book_ids)

    def get_all_books(
        self,
        page: int,
        per_page: int,
        sort_by: str,
        order: str,
        filters: dict,
    ) -> tuple[list[Book], int, int]:
        return self.store.book_repo.get_all_books(
            page=page, per_page=per_page, sort_by=sort_by, order=order, filters=filters
        )

    def search_books(  # noqa: PLR0913
        self,
        query: str,
        page: int,
        per_page: int,
        sort_by: str,
        order: str,
        filters: dict,
    ) -> tuple[list[Book], int, int]:
        return self.store.book_repo.get_searched_books(
            query, page=page, per_page=per_page, sort_by=sort_by, order=order, filters=filters
        )

    def get_books_by_tags(  # noqa: PLR0913
        self,
        tag_names: list[str],
        page: int,
        per_page: int,
        sort_by: str,
        order: str,
        filters: dict,
    ) -> tuple[list[Book], int, int]:
        return self.store.book_repo.get_books_by_tags(
            tag_names, page=page, per_page=per_page, sort_by=sort_by, order=order, filters=filters
        )

    def get_books_by_tag(
        self,
        tag_name: str,
        page: int,
        per_page: int,
        sort_by: str,
        order: str,
    ) -> tuple[list[Book], int, int]:
        return self.store.book_repo.get_books_by_tag(
            tag_name, page=page, per_page=per_page, sort_by=sort_by, order=order
        )

    def get_related_tags(self, tag_names: list[str]) -> list[Tag]:
        return self.store.book_repo.get_related_tags(tag_names)

    def get_tags_linked_to_books(self) -> list[Tag]:
        return self.store.book_repo.get_tags_linked_to_books()

    def filter_context(self) -> dict:
        return {
            "authors": self.store.book_repo.get_authors_linked_to_books(),
            "languages": self.store.book_repo.get_languages_linked_to_books(),
            "publishers": self.store.book_repo.get_publishers_linked_to_books(),
            "series_list": self.store.book_repo.get_series_linked_to_books(),
            "formats": self.store.book_repo.get_formats_linked_to_books(),
        }

    def edit_form_context(self) -> dict:
        return {
            "languages": self.store.book_repo.get_all_languages(),
            "authors": self.store.author_repo.list_all("name"),
            "publishers": self.store.publisher_repo.list_all("name"),
            "series_list": self.store.book_repo.get_all_series(),
            "formats": self.store.book_repo.get_formats_linked_to_books(),
        }

    def import_files(self, files: list[ImportedFile], tags: str) -> None:
        tag_set = {tag.strip() for tag in tags.lower().split(",") if tag.strip()}
        for file in files:
            file_type = file.content_type
            if file_type not in ALLOWED_TYPES:
                continue
            book_importer = ALLOWED_TYPES[file_type](file, tag_set)
            if not try_claim(book_importer.checksum):
                continue
            try:
                with self.transaction():
                    book_importer.process(self.store)
            finally:
                release(book_importer.checksum)

    def resync_metadata(self, book: Book) -> str | None:
        return resync_book_metadata(self.store, book)

    def unprotect_fields(self, book: Book) -> None:
        with self.transaction():
            reset_field_protection(book)

    def normalized_isbn(self, raw: str) -> str | None:
        isbn = normalize_isbn(raw)
        return canonical13(isbn) if isbn else None

    def edit_values(self, book: Book, dto: EditBookDTO | None = None) -> dict:
        if dto is not None:
            return {
                "title": dto.title,
                "authors": dto.author_names,
                "publisher": dto.publisher_name,
                "series": dto.series_name,
                "language_code": dto.language_code,
                "edition": dto.edition,
                "isbn": dto.isbn,
                "original_isbn": dto.original_isbn,
                "format": dto.format,
                "amazon_url": dto.amazon_url,
                "goodreads_url": dto.goodreads_url,
                "tags": dto.tags_str,
                "description": dto.description,
            }
        return {
            "title": book.title,
            "authors": ", ".join(author.name for author in book.authors),
            "publisher": book.publisher.name if book.publisher else "",
            "series": book.series.name if book.series else "",
            "language_code": book.language_code,
            "edition": book.edition or "",
            "isbn": book.isbn or "",
            "original_isbn": book.original_isbn or "",
            "format": book.format or "",
            "amazon_url": book.amazon_url or "",
            "goodreads_url": book.goodreads_url or "",
            "tags": ", ".join(tag.name for tag in book.tags),
            "description": book.description or "",
        }

    def lookup_values(self, book: Book, query: str) -> LookupResult:
        query = query.strip() or book.isbn or book.title or ""
        metadata = lookup_book(query)

        values = self.edit_values(book)
        if metadata is None:
            return LookupResult(values=values, error="No metadata found for the given query.")

        valid_language_codes = {lang.code for lang in self.store.book_repo.get_all_languages()}
        self.apply_lookup_values(values, metadata, valid_language_codes)
        if metadata.fuzzy:
            notice = {
                "message": f"Best match from {metadata.source} text search — not a direct ISBN record. Please verify it is the right book before saving.",
                "is_ok": True,
            }
        else:
            notice = {"message": f"Fetched from {metadata.source}. Review the fields and save.", "is_ok": True}
        return LookupResult(values=values, notice=notice)

    def apply_lookup_values(self, values: dict, metadata: BookMetadata, valid_language_codes: set[str]) -> dict:
        values["title"] = metadata.title
        values["authors"] = ", ".join(metadata.authors)
        if metadata.publisher:
            values["publisher"] = metadata.publisher
        if metadata.isbn:
            values["isbn"] = metadata.isbn
        if metadata.description:
            values["description"] = metadata.description
        if metadata.language_code in valid_language_codes:
            values["language_code"] = metadata.language_code
        return values

    def validate_edit(self, dto: EditBookDTO) -> EditValidation:
        language = self.store.session.get(Language, dto.language_code)
        errors = []
        if not dto.title or language is None:
            errors.append("Title and language are required.")
        normalized_book_isbn = self.normalized_isbn(dto.isbn)
        normalized_original_isbn = self.normalized_isbn(dto.original_isbn)
        if dto.isbn.strip() and normalized_book_isbn is None:
            errors.append("Invalid ISBN.")
        if dto.original_isbn.strip() and normalized_original_isbn is None:
            errors.append("Invalid original ISBN.")
        return EditValidation(errors=errors, isbn=normalized_book_isbn, original_isbn=normalized_original_isbn, language=language)

    def edited_fields(self, book: Book, dto: EditBookDTO, validation: EditValidation) -> list[str]:
        changed = []
        comparisons = [
            ("title", dto.title, book.title),
            ("description", dto.description.strip() or None, book.description),
            ("isbn", validation.isbn or None, book.isbn),
            ("original_isbn", validation.original_isbn or None, book.original_isbn),
            ("edition", dto.edition.strip() or None, book.edition),
            ("language", dto.language_code, book.language_code),
            ("authors", {name.strip() for name in dto.author_names.split(",") if name.strip()}, {author.name for author in book.authors}),
            ("publisher", dto.publisher_name.strip() or None, book.publisher.name if book.publisher else None),
            ("tags", {name.strip().lower() for name in dto.tags_str.split(",") if name.strip()}, {tag.name for tag in book.tags}),
            ("format", dto.format.strip() or None, book.format),
        ]
        for column, new_value, old_value in comparisons:
            if new_value != old_value:
                changed.append(column)
        return changed

    def apply_edit(self, book: Book, dto: EditBookDTO, validation: EditValidation) -> None:
        edited = self.edited_fields(book, dto, validation)
        with self.store.transaction():
            book.title = dto.title
            book.isbn = validation.isbn
            book.original_isbn = validation.original_isbn
            book.edition = dto.edition.strip() or None
            book.format = dto.format.strip() or None
            book.amazon_url = dto.amazon_url.strip() or None
            book.goodreads_url = dto.goodreads_url.strip() or None
            book.description = dto.description.strip() or None
            book.language = validation.language

            book.authors = self.resolve_authors(dto.author_names)
            book.publisher = self.resolve_publisher(dto.publisher_name)
            book.series = self.resolve_series(dto.series_name)
            book.tags = self.resolve_tags(dto.tags_str)

            mark_fields_updated(book, edited)

    def add_tag(self, book: Book, tag_name: str) -> None:
        tag = self.store.tag_repo.get_or_create(name=tag_name)
        self.store.book_repo.add_tag(book, tag)
        mark_fields_updated(book, ["tags"])

    def remove_tag(self, book: Book, tag_id: int) -> bool:
        tag = self.store.tag_repo.get_by_params(id=tag_id)
        if not tag:
            return False
        self.store.book_repo.remove_tag(book, tag)
        mark_fields_updated(book, ["tags"])
        return True

    def merge_tags(self, book_ids: list[int], tag_names: list[str]) -> None:
        with self.store.transaction():
            for book_id in book_ids:
                book = self.store.book_repo.get_book_by_id(book_id)
                if book:
                    new_tag_objects = {self.store.tag_repo.get_or_create(name=tag_name) for tag_name in tag_names}
                    existing_tags = set(book.tags)
                    merged_tags = existing_tags.union(new_tag_objects)
                    book.tags = list(merged_tags)
                    mark_fields_updated(book, ["tags"])

    def resolve_authors(self, author_names: str) -> list[Author]:
        authors = []
        seen_authors = set()
        for author_name in author_names.split(","):
            cleaned = author_name.strip()
            if not cleaned or cleaned.lower() in seen_authors:
                continue
            seen_authors.add(cleaned.lower())
            authors.append(self.store.author_repo.get_or_create(name=cleaned))
        return authors

    def resolve_publisher(self, publisher_name: str) -> Publisher | None:
        if publisher_name.strip():
            return self.store.publisher_repo.get_or_create(name=publisher_name.strip())
        return None

    def resolve_series(self, series_name: str) -> BookSeries | None:
        if not series_name.strip():
            return None
        series = self.store.session.scalar(select(BookSeries).where(BookSeries.name == series_name.strip()))
        if series is None:
            series = BookSeries(name=series_name.strip())
            self.store.session.add(series)
        return series

    def resolve_tags(self, tags_str: str) -> list[Tag]:
        tags = []
        for tag_name in tags_str.split(","):
            cleaned = tag_name.strip().lower()
            if not cleaned:
                continue
            tag = self.store.tag_repo.get_or_create(name=cleaned)
            if tag not in tags:
                tags.append(tag)
        return tags