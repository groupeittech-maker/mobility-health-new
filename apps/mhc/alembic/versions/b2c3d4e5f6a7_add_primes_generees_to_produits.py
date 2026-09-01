"""add primes_generees to produits_assurance

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-26

"""
from alembic import op


revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE produits_assurance ADD COLUMN IF NOT EXISTS primes_generees JSON"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE produits_assurance DROP COLUMN IF EXISTS primes_generees")
