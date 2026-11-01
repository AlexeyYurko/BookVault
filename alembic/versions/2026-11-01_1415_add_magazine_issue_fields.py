"""add magazine issue fields

Revision ID: 2e25de2b374b
Revises: a41c8f2d9e60
Create Date: 2026-11-01 14:15:31.163104

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2e25de2b374b'
down_revision: Union[str, Sequence[str], None] = 'a41c8f2d9e60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('books', sa.Column('publication_name', sa.String(), nullable=True))
    op.add_column('books', sa.Column('issue_number', sa.String(), nullable=True))
    op.add_column('books', sa.Column('issue_year', sa.Integer(), nullable=True))
    op.add_column('books', sa.Column('issue_month', sa.Integer(), nullable=True))
    op.add_column('books', sa.Column('issue_label', sa.String(), nullable=True))
    op.create_index('ix_books_issue_year', 'books', ['issue_year'], unique=False)
    op.create_index('ix_books_publication_name', 'books', ['publication_name'], unique=False)
    with op.batch_alter_table('books') as batch_op:
        batch_op.create_check_constraint(
            'ck_books_issue_month_range',
            "(issue_month IS NULL OR (issue_month >= 1 AND issue_month <= 12))",
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('books') as batch_op:
        batch_op.drop_constraint('ck_books_issue_month_range', type_='check')
    op.drop_index('ix_books_publication_name', table_name='books')
    op.drop_index('ix_books_issue_year', table_name='books')
    op.drop_column('books', 'issue_label')
    op.drop_column('books', 'issue_month')
    op.drop_column('books', 'issue_year')
    op.drop_column('books', 'issue_number')
    op.drop_column('books', 'publication_name')
