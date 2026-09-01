"""merge commission and contact heads

Revision ID: merge_commission_contact
Revises: e5f6a7b8c9d0, f1a2b3c4d5e6
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa


revision = 'merge_commission_contact'
down_revision = ('e5f6a7b8c9d0', 'f1a2b3c4d5e6')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
