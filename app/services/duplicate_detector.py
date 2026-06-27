from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

# Above this ratio (0-100), two titles are considered potential duplicates /
# editions of the same work. tuned for "Python Crash Course" vs
# "Python Crash Course, 2nd Edition" (token_set_ratio == 100).
TITLE_RATIO_THRESHOLD = 85

_RE_PUNCT = re.compile(r"[^\w\s]")


@dataclass(frozen=True)
class DuplicateHit:
    book_id: int
    title: str
    ratio: int


def _normalize(text: str) -> str:
    text = text.lower()
    text = _RE_PUNCT.sub(" ", text)
    return " ".join(text.split())


def _authors_share_any(new_authors: list[str], existing_authors: list[str]) -> bool:
    if not new_authors or not existing_authors:
        return False
    new_set = {_normalize(a) for a in new_authors}
    ex_set = {_normalize(a) for a in existing_authors}
    return bool(new_set & ex_set)


def find_similar(
    new_title: str,
    new_authors: list[str],
    existing: list[tuple[int, str, list[str]]],
) -> list[DuplicateHit]:
    """Detect titles in ``existing`` that fuzzy-match ``new_title``.

    ``existing`` is a list of ``(book_id, title, author_names)`` snapshots.

    Returns hits only; callers (SyncService) decide whether to assign the
    matched books to an edition group.
    """
    norm_new = _normalize(new_title)
    if not norm_new:
        return []

    hits: list[DuplicateHit] = []
    for book_id, ex_title, ex_authors in existing:
        if not _authors_share_any(new_authors, ex_authors):
            continue
        ratio = int(fuzz.token_set_ratio(norm_new, _normalize(ex_title)))
        if ratio > TITLE_RATIO_THRESHOLD:
            hits.append(DuplicateHit(book_id=book_id, title=ex_title, ratio=ratio))
    return hits