"""add e-card storage columns to attestations

Revision ID: a4d1c2b7316e
Revises: ef01ea5cc4b2
Create Date: 2025-11-24 10:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a4d1c2b7316e'
down_revision = 'ef01ea5cc4b2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('attestations', sa.Column('carte_numerique_path', sa.String(length=500), nullable=True))
    op.add_column('attestations', sa.Column('carte_numerique_bucket', sa.String(length=100), nullable=True))
    op.add_column('attestations', sa.Column('carte_numerique_url', sa.Text(), nullable=True))
    op.add_column('attestations', sa.Column('carte_numerique_expires_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('attestations', 'carte_numerique_expires_at')
    op.drop_column('attestations', 'carte_numerique_url')
    op.drop_column('attestations', 'carte_numerique_bucket')
    op.drop_column('attestations', 'carte_numerique_path')

