"""SQLite engine and SQLAlchemy session helpers."""

import os
from pathlib import Path
from typing import Generator

from fastapi import Request
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = REPOSITORY_ROOT / "backend" / "data" / "evaluator.sqlite3"


def get_database_url() -> str:
    """Return the configured database URL or the local SQLite default."""
    return os.environ.get("DATABASE_URL", "sqlite:///{}".format(DEFAULT_DATABASE_PATH))


def create_database_engine(database_url: str) -> Engine:
    """Create an engine, preparing local SQLite directories and foreign keys."""
    url = make_url(database_url)
    connect_args = {}
    if url.drivername.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if url.database and url.database != ":memory:":
            Path(url.database).expanduser().resolve().parent.mkdir(
                parents=True, exist_ok=True
            )

    engine = create_engine(database_url, connect_args=connect_args)
    if url.drivername.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _enable_sqlite_foreign_keys(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker:
    """Create request-scoped SQLAlchemy sessions for an engine."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db(request: Request) -> Generator[Session, None, None]:
    """Yield a session tied to the current application's engine."""
    factory: sessionmaker = request.app.state.session_factory
    session = factory()
    try:
        yield session
    finally:
        session.close()
