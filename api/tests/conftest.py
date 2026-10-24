"""Tests run against a real, disposable PostgreSQL database.

They truncate every table, so they refuse to run unless TEST_DATABASE_URL is set
explicitly (never point it at the dev or demo database).
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    pytest.exit(
        "Set TEST_DATABASE_URL to a disposable database, e.g. "
        "postgresql+asyncpg://h4t:h4t_dev_password@localhost:5432/h4t_test",
        returncode=2,
    )
# Must happen before `app` is imported: settings and the engine read DATABASE_URL.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("DEMO_MODE", "true")


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> Iterator[None]:
    from alembic import command
    from alembic.config import Config

    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "head")
    yield
