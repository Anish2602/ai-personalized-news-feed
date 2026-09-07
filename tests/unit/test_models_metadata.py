from __future__ import annotations

from app.db.models import Base


def test_all_core_tables_registered():
    tables = set(Base.metadata.tables)
    assert tables == {
        "users",
        "interests",
        "user_interests",
        "stories",
        "articles",
        "interactions",
        "processing_jobs",
        "user_profiles",
    }


def _unique_column_groups(table_name: str) -> set[tuple[str, ...]]:
    table = Base.metadata.tables[table_name]
    groups = {
        tuple(c.columns.keys())
        for c in table.constraints
        if c.__class__.__name__ == "UniqueConstraint"
    }
    groups |= {tuple(ix.columns.keys()) for ix in table.indexes if ix.unique}
    if table.primary_key is not None and len(table.primary_key.columns) > 1:
        groups.add(tuple(table.primary_key.columns.keys()))
    return groups


def test_article_url_is_unique():
    assert "url" in Base.metadata.tables["articles"].c
    assert ("url",) in _unique_column_groups("articles")


def test_user_email_is_unique():
    assert ("email",) in _unique_column_groups("users")


def test_user_interest_composite_unique():
    assert ("user_id", "interest_id") in _unique_column_groups("user_interests")
