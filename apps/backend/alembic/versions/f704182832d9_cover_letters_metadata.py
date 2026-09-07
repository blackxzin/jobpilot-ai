"""cover letters metadata (title, language, tone, updated_at)

Revision ID: f704182832d9
Revises: 8d93362cdfae
Create Date: 2026-08-19 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'f704182832d9'
down_revision: Union[str, None] = '8d93362cdfae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('cover_letters', sa.Column('title', sa.String(length=255), nullable=True))
    op.add_column('cover_letters', sa.Column('language', sa.String(length=10), nullable=True, server_default='pt-BR'))
    op.add_column('cover_letters', sa.Column('tone', sa.String(length=20), nullable=True, server_default='professional'))
    op.add_column('cover_letters', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('cover_letters', 'updated_at')
    op.drop_column('cover_letters', 'tone')
    op.drop_column('cover_letters', 'language')
    op.drop_column('cover_letters', 'title')
