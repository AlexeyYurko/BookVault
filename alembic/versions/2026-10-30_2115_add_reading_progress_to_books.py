"""add reading progress to books

Revision ID: 3f9c1d7a5b2e
Revises: f9209efe522c
Create Date: 2026-10-30 21:15:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '3f9c1d7a5b2e'
down_revision: Union[str, Sequence[str], None] = 'f9209efe522c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('books', sa.Column('reading_position', sa.String(), nullable=True))
    op.add_column('books', sa.Column('reading_percent', sa.Float(), nullable=True))
    op.add_column('books', sa.Column('reading_updated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('books', 'reading_updated_at')
    op.drop_column('books', 'reading_percent')
    op.drop_column('books', 'reading_position')
