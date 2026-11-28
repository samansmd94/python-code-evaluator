"""Create the exercise and official test catalog."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial_catalog"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "exercises",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("function_name", sa.String(length=100), nullable=False),
        sa.Column("function_signature", sa.String(length=240), nullable=False),
        sa.Column("difficulty", sa.String(length=20), nullable=False),
        sa.Column("requirements", sa.JSON(), nullable=False),
        sa.Column("examples", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "difficulty IN ('beginner', 'intermediate', 'advanced')",
            name="ck_exercises_difficulty",
        ),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_exercises_difficulty", "exercises", ["difficulty"])

    op.create_table(
        "test_suites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["exercise_id"], ["exercises.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("slug"),
        sa.UniqueConstraint("exercise_id", "version", name="uq_test_suites_version"),
    )
    op.create_index("ix_test_suites_exercise_id", "test_suites", ["exercise_id"])

    op.create_table(
        "test_cases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("test_suite_id", sa.Integer(), nullable=False),
        sa.Column("case_number", sa.Integer(), nullable=False),
        sa.Column("input_data", sa.JSON(), nullable=False),
        sa.Column("expected_output", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("case_number > 0", name="ck_test_cases_case_number"),
        sa.ForeignKeyConstraint(["test_suite_id"], ["test_suites.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "test_suite_id", "case_number", name="uq_test_case_number"
        ),
    )
    op.create_index("ix_test_cases_test_suite_id", "test_cases", ["test_suite_id"])


def downgrade() -> None:
    op.drop_index("ix_test_cases_test_suite_id", table_name="test_cases")
    op.drop_table("test_cases")
    op.drop_index("ix_test_suites_exercise_id", table_name="test_suites")
    op.drop_table("test_suites")
    op.drop_index("ix_exercises_difficulty", table_name="exercises")
    op.drop_table("exercises")
