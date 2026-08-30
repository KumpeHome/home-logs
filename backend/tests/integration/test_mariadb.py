import os

import pytest
from sqlalchemy import create_engine, inspect

import app.models  # noqa: F401
from app.db.base import Base


@pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set; start Compose profile test",
)
def test_mariadb_creates_core_tables() -> None:
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    Base.metadata.create_all(engine)
    names = set(inspect(engine).get_table_names())
    engine.dispose()
    assert "households" in names
    assert "household_members" in names
    assert "log_entries" in names
    assert "pdf_templates" in names
    assert "discipline_records" in names
    assert "household_otc_medications" in names
    assert "member_otc_assignments" in names
    assert "member_permissions" in names
