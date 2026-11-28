"""Exercise the initial Alembic upgrade and downgrade."""

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session

from backend.app.database import create_database_engine, create_session_factory
from backend.app.models import EvaluationRun, Exercise, Submission, TestSuite
from backend.app.seed import seed_initial_data
from .conftest import ALEMBIC_CONFIG


def test_initial_migration_creates_and_drops_catalog_tables(database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config(str(ALEMBIC_CONFIG))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    try:
        assert set(inspect(engine).get_table_names()) == {
            "alembic_version",
            "evaluation_runs",
            "exercises",
            "submissions",
            "test_cases",
            "test_results",
            "test_suites",
        }
    finally:
        engine.dispose()


def test_downgrade_maps_internal_error_to_supported_legacy_status(
    database_url, monkeypatch
):
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config(str(ALEMBIC_CONFIG))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")

    engine = create_database_engine(database_url)
    factory = create_session_factory(engine)
    try:
        with factory() as session:
            seed_initial_data(session)
            exercise = session.scalar(
                select(Exercise).where(Exercise.slug == "addition")
            )
            suite = session.scalar(
                select(TestSuite).where(TestSuite.slug == "addition-default-v1")
            )
            submission = Submission(
                exercise_id=exercise.id,
                test_suite_id=suite.id,
                source_code="def add(a, b): return a + b",
            )
            session.add(submission)
            session.flush()
            session.add(
                EvaluationRun(
                    submission_id=submission.id,
                    status="internal_error",
                    total_tests=0,
                    passed_tests=0,
                    failed_tests=0,
                    error_tests=0,
                    success_rate=0.0,
                    duration_ms=1,
                    failure_message="Evaluation could not be completed.",
                )
            )
            session.commit()
    finally:
        engine.dispose()

    command.downgrade(config, "0002_execution_history")
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            status_value = connection.scalar(
                text("SELECT status FROM evaluation_runs LIMIT 1")
            )
        assert status_value == "infrastructure_error"
    finally:
        engine.dispose()

    command.downgrade(config, "base")
    engine = create_engine(database_url)
    try:
        remaining_tables = set(inspect(engine).get_table_names()) - {"alembic_version"}
        assert remaining_tables == set()
    finally:
        engine.dispose()
