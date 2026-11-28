"""SQLAlchemy models for exercises, suites, and official test cases."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class shared by the backend's database models."""


class Exercise(Base):
    """A programming exercise available to users."""

    __test__ = False
    __tablename__ = "exercises"
    __table_args__ = (
        CheckConstraint(
            "difficulty IN ('beginner', 'intermediate', 'advanced')",
            name="ck_exercises_difficulty",
        ),
        Index("ix_exercises_difficulty", "difficulty"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    function_name: Mapped[str] = mapped_column(String(100), nullable=False)
    function_signature: Mapped[str] = mapped_column(String(240), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    requirements: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    examples: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    test_suites: Mapped[list["TestSuite"]] = relationship(
        back_populates="exercise", cascade="all, delete-orphan"
    )
    submissions: Mapped[list["Submission"]] = relationship(back_populates="exercise")


class TestSuite(Base):
    """A versioned collection of official test cases for an exercise."""

    __test__ = False
    __tablename__ = "test_suites"
    __table_args__ = (
        UniqueConstraint("exercise_id", "version", name="uq_test_suites_version"),
        Index("ix_test_suites_exercise_id", "exercise_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    exercise: Mapped[Exercise] = relationship(back_populates="test_suites")
    test_cases: Mapped[list["TestCase"]] = relationship(
        back_populates="test_suite", cascade="all, delete-orphan"
    )
    submissions: Mapped[list["Submission"]] = relationship(back_populates="test_suite")


class TestCase(Base):
    """One immutable-by-API input and expected output in a suite."""

    __test__ = False
    __tablename__ = "test_cases"
    __table_args__ = (
        UniqueConstraint("test_suite_id", "case_number", name="uq_test_case_number"),
        Index("ix_test_cases_test_suite_id", "test_suite_id"),
        CheckConstraint("case_number > 0", name="ck_test_cases_case_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    test_suite_id: Mapped[int] = mapped_column(
        ForeignKey("test_suites.id", ondelete="CASCADE"), nullable=False
    )
    case_number: Mapped[int] = mapped_column(Integer, nullable=False)
    input_data: Mapped[list] = mapped_column(JSON, nullable=False)
    expected_output: Mapped[object] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    test_suite: Mapped[TestSuite] = relationship(back_populates="test_cases")


class Submission(Base):
    """One submitted source file associated with a trusted exercise and suite."""

    __test__ = False
    __tablename__ = "submissions"
    __table_args__ = (
        CheckConstraint("length(source_code) <= 32768", name="ck_submissions_source_size"),
        Index("ix_submissions_exercise_id", "exercise_id"),
        Index("ix_submissions_test_suite_id", "test_suite_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.id", ondelete="RESTRICT"), nullable=False
    )
    test_suite_id: Mapped[int] = mapped_column(
        ForeignKey("test_suites.id", ondelete="RESTRICT"), nullable=False
    )
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    exercise: Mapped[Exercise] = relationship(back_populates="submissions")
    test_suite: Mapped[TestSuite] = relationship(back_populates="submissions")
    evaluation_run: Mapped["EvaluationRun"] = relationship(
        back_populates="submission", cascade="all, delete-orphan", uselist=False
    )


class EvaluationRun(Base):
    """Summary for one isolated evaluation attempt."""

    __test__ = False
    __tablename__ = "evaluation_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('completed', 'invalid_submission', 'timed_out', "
            "'infrastructure_error', 'internal_error')",
            name="ck_evaluation_runs_status",
        ),
        CheckConstraint("total_tests >= 0", name="ck_evaluation_runs_total_tests"),
        CheckConstraint("passed_tests >= 0", name="ck_evaluation_runs_passed_tests"),
        CheckConstraint("failed_tests >= 0", name="ck_evaluation_runs_failed_tests"),
        CheckConstraint("error_tests >= 0", name="ck_evaluation_runs_error_tests"),
        CheckConstraint("duration_ms >= 0", name="ck_evaluation_runs_duration"),
        CheckConstraint(
            "success_rate >= 0 AND success_rate <= 100",
            name="ck_evaluation_runs_success_rate",
        ),
        Index("ix_evaluation_runs_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    total_tests: Mapped[int] = mapped_column(Integer, nullable=False)
    passed_tests: Mapped[int] = mapped_column(Integer, nullable=False)
    failed_tests: Mapped[int] = mapped_column(Integer, nullable=False)
    error_tests: Mapped[int] = mapped_column(Integer, nullable=False)
    success_rate: Mapped[float] = mapped_column(nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    failure_message: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    submission: Mapped[Submission] = relationship(back_populates="evaluation_run")
    test_results: Mapped[list["TestResult"]] = relationship(
        back_populates="evaluation_run", cascade="all, delete-orphan"
    )


class TestResult(Base):
    """One test outcome, including snapshots for later history inspection."""

    __test__ = False
    __tablename__ = "test_results"
    __table_args__ = (
        UniqueConstraint(
            "evaluation_run_id", "case_number", name="uq_test_result_case"
        ),
        CheckConstraint(
            "status IN ('passed', 'failed', 'syntax_error', 'missing_function', "
            "'runtime_error', 'timeout', 'output_limit')",
            name="ck_test_results_status",
        ),
        CheckConstraint("case_number > 0", name="ck_test_results_case_number"),
        CheckConstraint("duration_ms >= 0", name="ck_test_results_duration"),
        Index("ix_test_results_evaluation_run_id", "evaluation_run_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evaluation_run_id: Mapped[int] = mapped_column(
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False
    )
    test_case_id: Mapped[int | None] = mapped_column(
        ForeignKey("test_cases.id", ondelete="SET NULL"), nullable=True
    )
    case_number: Mapped[int] = mapped_column(Integer, nullable=False)
    input_data: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    expected_output: Mapped[Any] = mapped_column(JSON, nullable=True)
    actual_output: Mapped[Any] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(200), nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    evaluation_run: Mapped[EvaluationRun] = relationship(back_populates="test_results")
