"""add commission_assureur_pct to produits_assurance

Revision ID: f1a2b3c4d5e6
Revises: a1b2c3d4e5f6
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa


revision = 'f1a2b3c4d5e6'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE produits_assurance "
        "ADD COLUMN IF NOT EXISTS commission_assureur_pct NUMERIC(5, 2) DEFAULT 30"
    )
    op.execute(
        "UPDATE produits_assurance SET commission_assureur_pct = 30 WHERE commission_assureur_pct IS NULL"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE produits_assurance DROP COLUMN IF EXISTS commission_assureur_pct")
