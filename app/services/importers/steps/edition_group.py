from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.models import Book
from app.services.duplicate_detector import find_similar
from app.services.importers.pipeline import PipelineStep

if TYPE_CHECKING:
    from app.services.importers.context import ImportContext

logger = logging.getLogger(__name__)


class EditionGroupStep(PipelineStep):
    def process(self, ctx: ImportContext) -> ImportContext:
        if not ctx.is_new or ctx.book is None:
            return ctx

        just_added = ctx.book
        new_authors = [a.name for a in just_added.authors]
        existing = self._load_author_scoped(ctx, new_authors, exclude_id=just_added.id)
        hits = find_similar(just_added.title, new_authors, existing)

        for hit in hits:
            logger.info(
                "Potential duplicate: book %d '%s' ~ book %d '%s' (ratio %d)",
                just_added.id, just_added.title, hit.book_id, hit.title, hit.ratio,
            )

        self._assign_edition_group(ctx, just_added, [h.book_id for h in hits])
        return ctx

    @staticmethod
    def _load_author_scoped(
        ctx: ImportContext,
        author_names: list[str],
        exclude_id: int,
    ) -> list[tuple[int, str, list[str]]]:
        if not author_names:
            return []
        books = (
            ctx.store.session
            .query(Book)
            .join(Book.authors)
            .filter(Book.id != exclude_id)
            .distinct()
            .all()
        )
        return [(b.id, b.title, [a.name for a in b.authors]) for b in books]

    @staticmethod
    def _assign_edition_group(
        ctx: ImportContext,
        just_added: Book,
        matched_ids: list[int],
    ) -> None:
        if not matched_ids:
            return
        matched_books = list(
            ctx.store.session.scalars(
                ctx.store.session.query(Book).filter(Book.id.in_(matched_ids))
            )
        )
        if not matched_books:
            return
        group = next((b.edition_group for b in matched_books if b.edition_group_id), None)
        if group is None:
            group_name = min(
                [just_added.title, *(b.title for b in matched_books)],
                key=len,
            )
            group = ctx.store.edition_group_repo.create(name=group_name)
        just_added.edition_group = group
        for b in matched_books:
            b.edition_group = group
        logger.info(
            "Grouped %d book(s) under edition_group_id=%s (anchor: %r)",
            len(matched_books) + 1, group.id, just_added.title,
        )