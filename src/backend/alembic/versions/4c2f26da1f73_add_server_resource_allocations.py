"""Add per-server CPU and memory allocations.

Revision ID: 4c2f26da1f73
Revises: 53aef23a9ef6
Create Date: 2026-07-19 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "4c2f26da1f73"
down_revision: str | Sequence[str] | None = "53aef23a9ef6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add positive CPU and memory allocations with safe defaults for existing Pumpkin rows."""
    with op.batch_alter_table("servers") as batch_op:
        batch_op.add_column(
            sa.Column(
                "cpu_millicores",
                sa.Integer(),
                server_default=sa.text("2000"),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "memory_bytes",
                sa.BigInteger(),
                server_default=sa.text("2147483648"),
                nullable=False,
            )
        )
        batch_op.create_check_constraint(
            "ck_servers_cpu_millicores_positive",
            "cpu_millicores > 0",
        )
        batch_op.create_check_constraint(
            "ck_servers_memory_bytes_positive",
            "memory_bytes > 0",
        )
    with op.batch_alter_table("servers") as batch_op:
        batch_op.alter_column(
            "cpu_millicores",
            existing_type=sa.Integer(),
            server_default=sa.text("1000"),
        )


def downgrade() -> None:
    """Remove per-server CPU and memory allocations."""
    with op.batch_alter_table("servers") as batch_op:
        batch_op.drop_constraint(
            "ck_servers_memory_bytes_positive",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_servers_cpu_millicores_positive",
            type_="check",
        )
        batch_op.drop_column("memory_bytes")
        batch_op.drop_column("cpu_millicores")
