"""add nationalite, numero_passeport, validite_passeport, contact_urgence to users

Revision ID: a1b2c3d4e5f6
Revises: 0f5d5cb10850
Create Date: 2026-01-26

"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = '0f5d5cb10850'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS nationalite VARCHAR")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS numero_passeport VARCHAR(50)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS validite_passeport DATE")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS contact_urgence VARCHAR(30)")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS contact_urgence")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS validite_passeport")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS numero_passeport")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS nationalite")
