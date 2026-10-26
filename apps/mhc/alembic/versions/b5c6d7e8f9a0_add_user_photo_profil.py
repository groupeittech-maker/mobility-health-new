"""Photo de profil MyMHC sur l'utilisateur.

Revision ID: b5c6d7e8f9a0
Revises: a4b5c6d7e8f9
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b5c6d7e8f9a0"
down_revision: Union[str, Sequence[str], None] = "a4b5c6d7e8f9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("photo_profil", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "photo_profil")
