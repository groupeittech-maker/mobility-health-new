"""Ajouter la table courtier_agents (portail agents intermédiaire).

Revision ID: a4b5c6d7e8f9
Revises: z3a4b5c6d7e8
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a4b5c6d7e8f9"
down_revision: Union[str, Sequence[str], None] = "z3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "courtier_agents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("courtier_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type_agent", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["courtier_id"], ["courtiers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_courtier_agent_user"),
    )
    op.create_index("ix_courtier_agents_id", "courtier_agents", ["id"])
    op.create_index("ix_courtier_agents_courtier_id", "courtier_agents", ["courtier_id"])
    op.create_index("ix_courtier_agents_user_id", "courtier_agents", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_courtier_agents_user_id", table_name="courtier_agents")
    op.drop_index("ix_courtier_agents_courtier_id", table_name="courtier_agents")
    op.drop_index("ix_courtier_agents_id", table_name="courtier_agents")
    op.drop_table("courtier_agents")
