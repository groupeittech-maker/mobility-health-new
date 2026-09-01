"""merge all heads

Revision ID: merge_all_heads
Revises: a45f38567462, create_assureur_agents, e46d145700d0
Create Date: 2025-12-04 21:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'merge_all_heads'
down_revision = ('a45f38567462', 'create_assureur_agents', 'e46d145700d0')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

