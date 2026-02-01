"""Add settings persistence tables and columns.

Revision ID: 20260127_add_settings_persistence
Revises:
Create Date: 2026-01-27 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260127_add_settings_persistence"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "user_settings",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column(
            "default_strict_mode",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "default_persona",
            sa.String(),
            nullable=False,
            server_default=sa.text("'default'"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.add_column(
        "conversations",
        sa.Column(
            "active_strict_mode",
            sa.Boolean(),
            nullable=True,
            server_default=sa.null(),
        ),
    )
    op.add_column(
        "conversations",
        sa.Column(
            "active_persona",
            sa.String(),
            nullable=True,
            server_default=sa.null(),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("conversations", "active_persona")
    op.drop_column("conversations", "active_strict_mode")
    op.drop_table("user_settings")
