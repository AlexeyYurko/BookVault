from __future__ import annotations

import re

ISBN10_LEN = 10
ISBN13_LEN = 13
ISBN10_X = 10
ISBN13_PREFIXES = {"978", "979"}

_RAW_PATTERN = re.compile(r"[\dXx][\dXx\- ]{9,21}[\dXx]")


def _check_digit_isbn10(digits: str) -> str:
    total = sum((10 - i) * int(d) for i, d in enumerate(digits[:9]))
    check = (11 - total % 11) % 11
    return "X" if check == ISBN10_X else str(check)


def _check_digit_isbn13(digits: str) -> str:
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits[:12]))
    return str((10 - total % 10) % 10)


def normalize_isbn(raw: str) -> str | None:
    """Parse and validate an ISBN-10/ISBN-13 string.

    Returns the canonical digits-only form (uppercased trailing "X" for
    ISBN-10) or ``None`` if the value is not a valid ISBN.
    """
    if not raw:
        return None
    candidate = re.sub(r"[^0-9Xx]", "", raw).upper()
    if len(candidate) == ISBN10_LEN and candidate[-1] == _check_digit_isbn10(candidate):
        return candidate
    if len(candidate) == ISBN13_LEN and candidate[:3] in ISBN13_PREFIXES and candidate[-1] == _check_digit_isbn13(candidate):
        return candidate
    return None


def canonical13(isbn: str) -> str:
    """13-digit canonical form of a normalized ISBN, to dedupe ISBN-10/ISBN-13 pairs."""
    if len(isbn) == ISBN13_LEN:
        return isbn
    if len(isbn) == ISBN10_LEN:
        return "978" + isbn[:9] + _check_digit_isbn13("978" + isbn[:9])
    return isbn


def extract_isbns(text: str) -> list[str]:
    """Scan free text, returning valid ISBNs in document order, deduped by canonical form."""
    if not text:
        return []
    seen: set[str] = set()
    result: list[str] = []
    for match in _RAW_PATTERN.finditer(text):
        isbn = normalize_isbn(match.group(0))
        if not isbn:
            continue
        if canonical13(isbn) in seen:
            continue
        seen.add(canonical13(isbn))
        result.append(isbn)
    return result


def extract_isbn_from_identifier(value: str, scheme: str | None = None) -> str | None:
    """Extract ISBN from an identifier declared in metadata (EPUB OPF etc.)."""
    if scheme and "isbn" in scheme.lower():
        return normalize_isbn(value.rsplit(":", 1)[-1])
    if "urn:isbn" in value.lower():
        return normalize_isbn(value.rsplit(":", 1)[-1])
    return normalize_isbn(value)