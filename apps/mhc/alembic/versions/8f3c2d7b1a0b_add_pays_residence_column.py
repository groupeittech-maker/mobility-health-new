"""add pays_residence column if missing

Revision ID: 8f3c2d7b1a0b
Revises: merge_all_heads
Create Date: 2026-01-25 12:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '8f3c2d7b1a0b'
down_revision = 'merge_all_heads'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Guarded for environments where earlier migrations were not applied.
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS pays_residence VARCHAR")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS pays_residence")
