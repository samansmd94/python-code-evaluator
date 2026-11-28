"""Allow recorded internal evaluation failures as terminal runs."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_internal_evaluation_error"
down_revision: Union[str, None] = "0002_execution_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("evaluation_runs") as batch_op:
        batch_op.drop_constraint("ck_evaluation_runs_status", type_="check")
        batch_op.create_check_constraint(
            "ck_evaluation_runs_status",
            "status IN ('completed', 'invalid_submission', 'timed_out', "
            "'infrastructure_error', 'internal_error')",
        )


def downgrade() -> None:
    op.get_bind().execute(
        sa.text(
            "UPDATE evaluation_runs "
            "SET status = 'infrastructure_error' "
            "WHERE status = 'internal_error'"
        )
    )
    with op.batch_alter_table("evaluation_runs") as batch_op:
        batch_op.drop_constraint("ck_evaluation_runs_status", type_="check")
        batch_op.create_check_constraint(
            "ck_evaluation_runs_status",
            "status IN ('completed', 'invalid_submission', 'timed_out', "
            "'infrastructure_error')",
        )
