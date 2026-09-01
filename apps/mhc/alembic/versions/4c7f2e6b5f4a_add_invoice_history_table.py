"""add invoice history table

Revision ID: 4c7f2e6b5f4a
Revises: 3f0c4e98c9b2
Create Date: 2025-01-24 15:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4c7f2e6b5f4a"
down_revision: Union[str, Sequence[str], None] = ("3f0c4e98c9b2", "b2b5c1aa3d6d")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "invoice_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("previous_status", sa.String(length=30), nullable=True),
        sa.Column("new_status", sa.String(length=30), nullable=True),
        sa.Column("previous_stage", sa.String(length=30), nullable=True),
        sa.Column("new_stage", sa.String(length=30), nullable=True),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_invoice_history_actor_id"),
        "invoice_history",
        ["actor_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_invoice_history_id"),
        "invoice_history",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_invoice_history_invoice_id"),
        "invoice_history",
        ["invoice_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_invoice_history_invoice_id"), table_name="invoice_history")
    op.drop_index(op.f("ix_invoice_history_actor_id"), table_name="invoice_history")
    op.drop_index(op.f("ix_invoice_history_id"), table_name="invoice_history")
    op.drop_table("invoice_history")


