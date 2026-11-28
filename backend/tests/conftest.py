"""Shared temporary database and API fixtures for backend tests."""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from backend.app.main import create_app

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_CONFIG = REPOSITORY_ROOT / "backend" / "alembic.ini"


def upgrade_schema(database_url: str, monkeypatch) -> None:
    """Apply the checked-in Alembic revisions to the given database."""
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config(str(ALEMBIC_CONFIG))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")


@pytest.fixture
def database_url(tmp_path: Path) -> str:
    return "sqlite:///{}".format(tmp_path / "test.sqlite3")


@pytest.fixture
def migrated_database(database_url: str, monkeypatch) -> str:
    upgrade_schema(database_url, monkeypatch)
    return database_url


@pytest.fixture
def client(migrated_database: str):
    app = create_app(migrated_database)
    with TestClient(app) as test_client:
        yield test_client
