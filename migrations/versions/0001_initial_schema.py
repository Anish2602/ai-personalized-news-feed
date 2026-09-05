"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-05

Creates: users, interests, user_interests, stories, articles, interactions,
processing_jobs — plus the enum types they depend on.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# create_type=False: the types are created/dropped explicitly below so that
# op.create_table() does not also try to emit CREATE TYPE.
article_status = postgresql.ENUM(
    "PENDING", "PROCESSING", "COMPLETED", "FAILED",
    name="article_processing_status", create_type=False,
)
job_status = postgresql.ENUM(
    "PENDING", "PROCESSING", "COMPLETED", "FAILED",
    name="processing_job_status", create_type=False,
)
interaction_type = postgresql.ENUM(
    "VIEW", "CLICK", "LIKE", "DISLIKE", "SAVE", "SKIP", "SHARE",
    name="interaction_type", create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    article_status.create(bind, checkfirst=True)
    job_status.create(bind, checkfirst=True)
    interaction_type.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )

    op.create_table(
        "interests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interests")),
        sa.UniqueConstraint("name", name=op.f("uq_interests_name")),
    )

    op.create_table(
        "user_interests",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("interest_id", sa.Uuid(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_user_interests_user_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["interest_id"],
            ["interests.id"],
            name=op.f("fk_user_interests_interest_id_interests"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "interest_id", name=op.f("pk_user_interests")),
    )

    op.create_table(
        "stories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("canonical_title", sa.String(length=500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stories")),
    )

    op.create_table(
        "articles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("story_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("source", sa.String(length=200), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("embedding_reference", sa.String(length=128), nullable=True),
        sa.Column(
            "processing_status",
            article_status,
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["story_id"], ["stories.id"], name=op.f("fk_articles_story_id_stories"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_articles")),
        sa.UniqueConstraint("url", name=op.f("uq_articles_url")),
    )
    op.create_index(op.f("ix_articles_story_id"), "articles", ["story_id"], unique=False)
    op.create_index(op.f("ix_articles_source"), "articles", ["source"], unique=False)
    op.create_index(op.f("ix_articles_published_at"), "articles", ["published_at"], unique=False)
    op.create_index(
        op.f("ix_articles_processing_status"), "articles", ["processing_status"], unique=False
    )

    op.create_table(
        "interactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("interaction_type", interaction_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_interactions_user_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["article_id"],
            ["articles.id"],
            name=op.f("fk_interactions_article_id_articles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interactions")),
    )
    op.create_index(
        "ix_interactions_user_created", "interactions", ["user_id", "created_at"], unique=False
    )
    op.create_index(
        "ix_interactions_article_type",
        "interactions",
        ["article_id", "interaction_type"],
        unique=False,
    )

    op.create_table(
        "processing_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("status", job_status, nullable=False, server_default="PENDING"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["article_id"],
            ["articles.id"],
            name=op.f("fk_processing_jobs_article_id_articles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_processing_jobs")),
    )
    op.create_index(
        op.f("ix_processing_jobs_article_id"), "processing_jobs", ["article_id"], unique=False
    )
    op.create_index(op.f("ix_processing_jobs_status"), "processing_jobs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_table("processing_jobs")
    op.drop_table("interactions")
    op.drop_table("articles")
    op.drop_table("stories")
    op.drop_table("user_interests")
    op.drop_table("interests")
    op.drop_table("users")

    bind = op.get_bind()
    interaction_type.drop(bind, checkfirst=True)
    job_status.drop(bind, checkfirst=True)
    article_status.drop(bind, checkfirst=True)
