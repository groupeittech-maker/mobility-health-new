"""add courtier agent comptable link

Revision ID: w1x2y3z4a5b6
Revises: v2c3d4e5f6g7
Create Date: 2026-04-08 18:45:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "w1x2y3z4a5b6"
down_revision = "v2c3d4e5f6g7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "courtiers",
        sa.Column("agent_comptable_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f("ix_courtiers_agent_comptable_id"),
        "courtiers",
        ["agent_comptable_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_courtiers_agent_comptable_id",
        "courtiers",
        "users",
        ["agent_comptable_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_courtiers_agent_comptable_id", "courtiers", type_="foreignkey")
    op.drop_index(op.f("ix_courtiers_agent_comptable_id"), table_name="courtiers")
    op.drop_column("courtiers", "agent_comptable_id")

