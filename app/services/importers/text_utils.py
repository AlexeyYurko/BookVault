import html
import re

TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")

AUTHOR_SEPARATORS = (" and ", " / ")


def parse_authors(raw: str | None) -> list[str]:
    """Split a raw author string into individual names.

    Tries Dublin Core (" and ") then PDF-style (" / ") separators before
    falling back to treating the value as a single author, so that names in
    "Lastname, Firstname" form are not split on the comma.
    """
    if not raw:
        return []

    for separator in AUTHOR_SEPARATORS:
        if separator in raw:
            names = [name.strip() for name in raw.split(separator)]
            authors = [name for name in names if name]
            if len(authors) > 1:
                return authors

    return [raw.strip()] if raw.strip() else []


def clean_description(raw: str | None) -> str | None:
    """Strip HTML tags and decode entities from a raw description."""
    if not raw:
        return raw

    text = TAG_RE.sub(" ", raw)
    text = html.unescape(text)
    return WHITESPACE_RE.sub(" ", text).strip()
