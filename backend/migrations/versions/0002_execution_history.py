"""Add submissions, evaluation runs, and per-test results."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_execution_history"
down_revision: Union[str, None] = "0001_initial_catalog"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "submissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.Column("test_suite_id", sa.Integer(), nullable=False),
        sa.Column("source_code", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(source_code) <= 32768", name="ck_submissions_source_size"
        ),
        sa.ForeignKeyConstraint(
            ["exercise_id"], ["exercises.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["test_suite_id"], ["test_suites.id"], ondelete="RESTRICT"
        ),
    )
    op.create_index("ix_submissions_exercise_id", "submissions", ["exercise_id"])
    op.create_index("ix_submissions_test_suite_id", "submissions", ["test_suite_id"])

    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("total_tests", sa.Integer(), nullable=False),
        sa.Column("passed_tests", sa.Integer(), nullable=False),
        sa.Column("failed_tests", sa.Integer(), nullable=False),
        sa.Column("error_tests", sa.Integer(), nullable=False),
        sa.Column("success_rate", sa.Float(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("failure_message", sa.String(length=200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('completed', 'invalid_submission', 'timed_out', 'infrastructure_error')",
            name="ck_evaluation_runs_status",
        ),
        sa.CheckConstraint("total_tests >= 0", name="ck_evaluation_runs_total_tests"),
        sa.CheckConstraint("passed_tests >= 0", name="ck_evaluation_runs_passed_tests"),
        sa.CheckConstraint("failed_tests >= 0", name="ck_evaluation_runs_failed_tests"),
        sa.CheckConstraint("error_tests >= 0", name="ck_evaluation_runs_error_tests"),
        sa.CheckConstraint("duration_ms >= 0", name="ck_evaluation_runs_duration"),
        sa.CheckConstraint(
            "success_rate >= 0 AND success_rate <= 100",
            name="ck_evaluation_runs_success_rate",
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"], ["submissions.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("submission_id"),
    )
    op.create_index("ix_evaluation_runs_created_at", "evaluation_runs", ["created_at"])

    op.create_table(
        "test_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("evaluation_run_id", sa.Integer(), nullable=False),
        sa.Column("test_case_id", sa.Integer(), nullable=True),
        sa.Column("case_number", sa.Integer(), nullable=False),
        sa.Column("input_data", sa.JSON(), nullable=False),
        sa.Column("expected_output", sa.JSON(), nullable=True),
        sa.Column("actual_output", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.String(length=200), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "status IN ('passed', 'failed', 'syntax_error', 'missing_function', "
            "'runtime_error', 'timeout', 'output_limit')",
            name="ck_test_results_status",
        ),
        sa.CheckConstraint("case_number > 0", name="ck_test_results_case_number"),
        sa.CheckConstraint("duration_ms >= 0", name="ck_test_results_duration"),
        sa.ForeignKeyConstraint(
            ["evaluation_run_id"], ["evaluation_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["test_case_id"], ["test_cases.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint(
            "evaluation_run_id", "case_number", name="uq_test_result_case"
        ),
    )
    op.create_index(
        "ix_test_results_evaluation_run_id", "test_results", ["evaluation_run_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_test_results_evaluation_run_id", table_name="test_results")
    op.drop_table("test_results")
    op.drop_index("ix_evaluation_runs_created_at", table_name="evaluation_runs")
    op.drop_table("evaluation_runs")
    op.drop_index("ix_submissions_test_suite_id", table_name="submissions")
    op.drop_index("ix_submissions_exercise_id", table_name="submissions")
    op.drop_table("submissions")
