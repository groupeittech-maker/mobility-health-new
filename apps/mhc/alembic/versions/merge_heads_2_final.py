"""Merge remaining heads into one (single head for upgrade head)

Revision ID: merge_heads_2
Revises: merge_heads_1, 9c2d6c5eaa11, b2b5c1aa3d6d
Create Date: 2025-02-07

"""
from alembic import op


revision = "merge_heads_2"
down_revision = ("merge_heads_1", "9c2d6c5eaa11", "b2b5c1aa3d6d")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
