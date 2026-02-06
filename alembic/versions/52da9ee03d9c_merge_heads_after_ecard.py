"""merge heads after ecard

Revision ID: 52da9ee03d9c
Revises: 1d8de8a2f4ce, a4d1c2b7316e
Create Date: 2025-11-24 18:30:26.066223

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '52da9ee03d9c'
down_revision = ('1d8de8a2f4ce', 'a4d1c2b7316e')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass


