from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Protocol

import httpx

from app.services.importers.isbn import canonical13, normalize_isbn

logger = logging.getLogger(__name__)

TIMEOUT = httpx.Timeout(10.0)
GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"
OPEN_LIBRARY_ISBN_URL = "https://openlibrary.org/api/books"
OPEN_LIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"

LANGUAGE_CODES = {
    "ara": "ar",
    "ces": "cs",
    "deu": "de",
    "eng": "en",
    "spa": "es",
    "fra": "fr",
    "fre": "fr",
    "ger": "de",
    "heb": "he",
    "ita": "it",
    "jpn": "ja",
    "nld": "nl",
    "pol": "pl",
    "por": "pt",
    "rus": "ru",
    "swe": "sv",
    "zho": "zh",
}


def normalize_language_code(code: str | None) -> str | None:
    code = (code or "").split("-")[0].split("_")[0].strip().lower()
    return LANGUAGE_CODES.get(code, code or None)


@dataclass
class BookMetadata:
    title: str
    authors: list[str] = field(default_factory=list)
    publisher: str | None = None
    isbn: str | None = None
    language_code: str | None = None
    description: str | None = None
    source: str = ""
    fuzzy: bool = False


class MetadataProvider(Protocol):
    def lookup(self, query: str, isbn: str | None) -> BookMetadata | None:
        """Return metadata for the query/ISBN, or None when this source has nothing."""
        ...


class GoogleBooksProvider:
    def __init__(self, client: httpx.Client):
        self.client = client

    def lookup(self, query: str, isbn: str | None) -> BookMetadata | None:
        params = {"q": f"isbn:{isbn}" if isbn else query, "maxResults": 1}
        try:
            response = self.client.get(GOOGLE_BOOKS_URL, params=params)
            response.raise_for_status()
            items = response.json().get("items") or []
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Google Books lookup failed: %s", exc)
            return None
        if not items:
            return None

        volume = items[0].get("volumeInfo") or {}
        title = volume.get("title")
        if not title and len(items) > 1:
            volume = items[1].get("volumeInfo") or {}
            title = volume.get("title")
        if not title:
            return None

        identifiers = {item.get("type"): item.get("identifier") for item in volume.get("industryIdentifiers") or []}
        authors = volume.get("authors") or []
        if isinstance(authors, str):
            authors = [authors]

        return BookMetadata(
            title=title,
            authors=[a for a in authors if isinstance(a, str)] or [],
            publisher=volume.get("publisher"),
            isbn=identifiers.get("ISBN_13") or identifiers.get("ISBN_10"),
            language_code=normalize_language_code(volume.get("language")),
            description=volume.get("description"),
            source="Google Books",
        )


class OpenLibraryEditionProvider:
    def __init__(self, client: httpx.Client):
        self.client = client

    def lookup(self, query: str, isbn: str | None) -> BookMetadata | None:
        if not isbn:
            return None

        params = {"bibkeys": f"ISBN:{isbn}", "jscmd": "data", "format": "json"}
        try:
            response = self.client.get(OPEN_LIBRARY_ISBN_URL, params=params)
            response.raise_for_status()
            edition = response.json().get(f"ISBN:{isbn}") or {}
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Open Library ISBN lookup failed: %s", exc)
            return None
        title = edition.get("title")
        if not title:
            return None

        authors = [a.get("name", "") for a in edition.get("authors") or [] if a.get("name")]
        publishers = [p.get("name", "") for p in edition.get("publishers") or [] if p.get("name")]
        language_code = None
        for language in edition.get("languages") or []:
            key = language.get("key", "")
            if "/languages/" in key:
                language_code = key.rsplit("/", 1)[-1]
                break
        description = edition.get("description")
        if isinstance(description, dict):
            description = description.get("value")

        return BookMetadata(
            title=title,
            authors=authors,
            publisher=publishers[0] if publishers else None,
            isbn=isbn,
            language_code=normalize_language_code(language_code),
            description=description,
            source="Open Library",
        )


class OpenLibrarySearchProvider:
    def __init__(self, client: httpx.Client):
        self.client = client

    def lookup(self, query: str, isbn: str | None) -> BookMetadata | None:
        params = {
            "q": isbn or query,
            "limit": 1,
            "fields": "title,author_name,publisher,isbn,language",
        }
        try:
            response = self.client.get(OPEN_LIBRARY_SEARCH_URL, params=params)
            response.raise_for_status()
            docs = response.json().get("docs") or []
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Open Library search failed: %s", exc)
            return None
        if not docs:
            return None

        doc = docs[0]
        title = doc.get("title")
        if not title:
            return None

        isbns = doc.get("isbn") or []
        found_isbn = next((value for value in isbns if normalize_isbn(value)), None)
        fuzzy = False
        if isbn:
            if canonical13(isbn) in {canonical13(value) for value in isbns}:
                found_isbn = isbn
            else:
                fuzzy = True
        languages = doc.get("language") or []
        publishers = doc.get("publisher") or []

        return BookMetadata(
            title=title,
            authors=[a for a in doc.get("author_name") or [] if isinstance(a, str)],
            publisher=publishers[0] if publishers else None,
            isbn=found_isbn,
            language_code=normalize_language_code(languages[0]) if languages else None,
            source="Open Library",
            fuzzy=fuzzy,
        )


ProvidersFactory = Callable[[httpx.Client, str | None], Sequence[MetadataProvider]]


def default_providers(client: httpx.Client, isbn: str | None) -> list[MetadataProvider]:
    """Providers in fallback order; the edition lookup only makes sense with an ISBN."""
    providers: list[MetadataProvider] = [GoogleBooksProvider(client)]
    if isbn:
        providers.append(OpenLibraryEditionProvider(client))
    providers.append(OpenLibrarySearchProvider(client))
    return providers


class MetadataLookup:
    def __init__(self, providers_factory: ProvidersFactory = default_providers):
        self._providers_factory = providers_factory

    def lookup(self, query: str) -> BookMetadata | None:
        """Return the first provider's metadata for the query, or None."""
        query = query.strip()
        if not query:
            return None

        isbn = normalize_isbn(query)
        with httpx.Client(timeout=TIMEOUT) as client:
            for provider in self._providers_factory(client, isbn):
                metadata = provider.lookup(query, isbn)
                if metadata is not None:
                    return metadata
        return None
