"""merge role_id and destination_country heads

Revision ID: merge_final_2
Revises: f0e1d2c3b4a5, a9b8c7d6e5f4
Create Date: 2025-02-04

Merges the two branch heads so 'alembic upgrade head' has a single target.
"""
from alembic import op


revision = 'merge_final_2'
down_revision = ('f0e1d2c3b4a5', 'a9b8c7d6e5f4')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
