"""add fcm_registration_token to users for mobile push

Revision ID: p1q2r3s4t5u6
Revises: o1p2q3r4s5t6
Create Date: 2026-03-26

"""
from alembic import op
import sqlalchemy as sa


revision = "p1q2r3s4t5u6"
down_revision = "o1p2q3r4s5t6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("fcm_registration_token", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "fcm_registration_token")
