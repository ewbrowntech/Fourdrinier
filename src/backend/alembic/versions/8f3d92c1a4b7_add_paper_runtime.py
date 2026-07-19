"""Allow the paper value in the server runtime constraint.

Revision ID: 8f3d92c1a4b7
Revises: 4c2f26da1f73
Create Date: 2026-07-19 18:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "8f3d92c1a4b7"
down_revision: str | Sequence[str] | None = "4c2f26da1f73"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Widen the server runtime check constraint to include paper."""
    with op.batch_alter_table("servers") as batch_op:
        batch_op.drop_constraint("server_runtime", type_="check")
        batch_op.create_check_constraint(
            "server_runtime",
            "runtime IN ('paper', 'pumpkin')",
        )


def downgrade() -> None:
    """Restore the pumpkin-only server runtime check constraint.

    Fails if any server row still uses the paper runtime; delete those rows
    before downgrading.
    """
    with op.batch_alter_table("servers") as batch_op:
        batch_op.drop_constraint("server_runtime", type_="check")
        batch_op.create_check_constraint(
            "server_runtime",
            "runtime IN ('pumpkin')",
        )
