"""Merge first 3 Alembic heads (role, users, souscription statut)

Revision ID: merge_heads_1
Revises: a7f8e9d0c1b2, b1c2d3e4f5a6, f2a3b4c5d6e7
Create Date: 2025-02-07

"""
from alembic import op


revision = "merge_heads_1"
down_revision = ("a7f8e9d0c1b2", "b1c2d3e4f5a6", "f2a3b4c5d6e7")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
