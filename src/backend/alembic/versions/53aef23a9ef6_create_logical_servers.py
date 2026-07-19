"""Create provider-independent logical servers.

Revision ID: 53aef23a9ef6
Revises: 0650701822cd
Create Date: 2026-07-17 17:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "53aef23a9ef6"
down_revision: str | Sequence[str] | None = "0650701822cd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the logical server table and its invariants."""
    op.create_table(
        "servers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "runtime",
            sa.Enum(
                "pumpkin",
                name="server_runtime",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            server_default=sa.text("'pumpkin'"),
            nullable=False,
        ),
        sa.Column("minecraft_version", sa.String(length=32), nullable=False),
        sa.Column(
            "desired_state",
            sa.Enum(
                "running",
                "stopped",
                name="server_desired_state",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            server_default=sa.text("'stopped'"),
            nullable=False,
        ),
        sa.Column("spec_generation", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "spec_generation >= 1",
            name="ck_servers_spec_generation_positive",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_servers_name"),
    )


def downgrade() -> None:
    """Drop the logical server table."""
    op.drop_table("servers")
