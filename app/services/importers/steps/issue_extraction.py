from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.services.importers.pipeline import PipelineStep

if TYPE_CHECKING:
    from app.services.importers.context import ImportContext


MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

SPECIAL_LABELS = [
    (re.compile(r"\b(xmas|christmas)\b", re.IGNORECASE), "Christmas Edition"),
    (re.compile(r"\bhalloween\b", re.IGNORECASE), "Halloween Special"),
    (re.compile(r"\bholiday\b", re.IGNORECASE), "Holiday Edition"),
    (re.compile(r"\bwinter\b", re.IGNORECASE), "Winter Special"),
    (re.compile(r"\bsummer\b", re.IGNORECASE), "Summer Special"),
    (re.compile(r"\bspring\b", re.IGNORECASE), "Spring Special"),
    (re.compile(r"\bautumn\b", re.IGNORECASE), "Autumn Special"),
    (re.compile(r"\bfal{2}\b", re.IGNORECASE), "Fall Special"),
    (re.compile(r"\banniversary\b", re.IGNORECASE), "Anniversary Edition"),
    (re.compile(r"\bcollectors?\s+edition\b", re.IGNORECASE), "Collector's Edition"),
    (re.compile(r"\bcollectors?\b", re.IGNORECASE), "Collector's Edition"),
    (re.compile(r"\brewind\b", re.IGNORECASE), "Rewind Edition"),
    (re.compile(r"\bbest\s+of\b", re.IGNORECASE), "Best Of"),
    (re.compile(r"\byearbook\b", re.IGNORECASE), "Yearbook"),
    (re.compile(r"\bspecial\b", re.IGNORECASE), "Special Edition"),
]

YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")
ISSUE_RE = re.compile(r"(?:#|issue|no\.?|nummer)\s*(\d+(?:[-/]\d+)?)\b", re.IGNORECASE)
MONTH_YEAR_RE = re.compile(
    r"\b(jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august|sep|sept|september|oct|october|nov|november|dec|december)[.\s/-]+(19\d{2}|20\d{2})\b",
    re.IGNORECASE,
)
YEAR_MONTH_RE = re.compile(r"\b(19\d{2}|20\d{2})[.\s/-]+(0?[1-9]|1[0-2])\b")
MONTH_NUM_RE = re.compile(r"\b(0?[1-9]|1[0-2])[.\s/-]+(19\d{2}|20\d{2})\b")


def _find_special_label(text: str) -> str | None:
    for pattern, label in SPECIAL_LABELS:
        if pattern.search(text):
            return label
    return None


def _extract_month_year(text: str, target) -> None:
    match = MONTH_YEAR_RE.search(text)
    if match:
        target.issue_month = MONTHS.get(match.group(1).lower())
        if target.issue_year is None and match.group(2):
            target.issue_year = int(match.group(2))
        return
    match = YEAR_MONTH_RE.search(text)
    if match:
        target.issue_month = int(match.group(2))
        if target.issue_year is None:
            target.issue_year = int(match.group(1))
        return
    match = MONTH_NUM_RE.search(text)
    if match:
        target.issue_month = int(match.group(1))
        if target.issue_year is None:
            target.issue_year = int(match.group(2))


class IssueExtractionStep(PipelineStep):
    def process(self, ctx: ImportContext) -> ImportContext:
        catalog = getattr(ctx.importer, "catalog", None)
        if catalog is None or getattr(catalog, "kind", None) != "magazine":
            return ctx

        text_parts = []
        if ctx.importer.file_path:
            text_parts.append(ctx.importer.file_path)
        if ctx.metadata and ctx.metadata.title:
            text_parts.append(ctx.metadata.title)
        text = " / ".join(text_parts)

        target = ctx.book if ctx.book is not None else ctx

        if getattr(target, "publication_name", None) is None and ctx.metadata and ctx.metadata.title:
            target.publication_name = ctx.metadata.title

        issue_label = _find_special_label(text)
        if issue_label and getattr(target, "issue_label", None) is None:
            target.issue_label = issue_label

        if getattr(target, "issue_year", None) is None:
            match = YEAR_RE.search(text)
            if match:
                target.issue_year = int(match.group(1))

        if getattr(target, "issue_month", None) is None:
            _extract_month_year(text, target)

        if getattr(target, "issue_number", None) is None:
            match = ISSUE_RE.search(text)
            if match:
                target.issue_number = match.group(1)

        if ctx.book is not None:
            ctx.book_publication_name = ctx.book.publication_name
            ctx.book_issue_number = ctx.book.issue_number
            ctx.book_issue_year = ctx.book.issue_year
            ctx.book_issue_month = ctx.book.issue_month
            ctx.book_issue_label = ctx.book.issue_label
        else:
            ctx.book_publication_name = getattr(target, "publication_name", None)
            ctx.book_issue_number = getattr(target, "issue_number", None)
            ctx.book_issue_year = getattr(target, "issue_year", None)
            ctx.book_issue_month = getattr(target, "issue_month", None)
            ctx.book_issue_label = getattr(target, "issue_label", None)
        return ctx
