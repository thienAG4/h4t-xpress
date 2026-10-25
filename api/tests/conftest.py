"""Tests run against a real, disposable PostgreSQL database.

They truncate every table, so they refuse to run unless TEST_DATABASE_URL is set
explicitly (never point it at the dev or demo database).
"""

import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    pytest.exit(
        "Set TEST_DATABASE_URL to a disposable database, e.g. "
        "postgresql+asyncpg://h4t:h4t_dev_password@localhost:5432/h4t_test",
        returncode=2,
    )
# Must happen before `app` is imported: settings and the engine read these variables.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["DEMO_MODE"] = "true"
os.environ["DEMO_PASSWORD"] = "Demo@12345"
os.environ["WORKER_ENABLED"] = "false"  # tests call the job functions directly

from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.main import app  # noqa: E402
from app.modules.auth.service import reset_limiters  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> Iterator[None]:
    from alembic import command
    from alembic.config import Config

    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "head")
    yield


@pytest_asyncio.fixture(scope="session", autouse=True)
async def seeded_database(migrated_database: None) -> None:
    """Small, fast data set shared by the API tests (2 days of history)."""
    from app.seed.runner import run_seed

    await run_seed(reset=True, history_days=2, random_seed=5)


@pytest.fixture(autouse=True)
def _clean_rate_limits() -> None:
    reset_limiters()


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver.local"
    ) as http:
        yield http
