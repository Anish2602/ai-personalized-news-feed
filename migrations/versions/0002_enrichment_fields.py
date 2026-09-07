"""enrichment fields: article.topics, story.topics, story.key_points

Revision ID: 0002_enrichment
Revises: 0001_initial
Create Date: 2026-09-07
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_enrichment"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "articles",
        sa.Column(
            "topics", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
    )
    op.add_column(
        "stories",
        sa.Column(
            "key_points",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "stories",
        sa.Column(
            "topics", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
    )


def downgrade() -> None:
    op.drop_column("stories", "topics")
    op.drop_column("stories", "key_points")
    op.drop_column("articles", "topics")
