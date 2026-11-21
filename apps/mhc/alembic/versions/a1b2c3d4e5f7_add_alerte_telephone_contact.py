"""Ajout du téléphone de contact de l'alerte SOS.

Revision ID: a1b2c3d4e5f7
Revises: z9a8b7c6d5e4
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, Sequence[str], None] = "z9a8b7c6d5e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("alertes", sa.Column("telephone_contact", sa.String(length=40), nullable=True))


def downgrade() -> None:
    op.drop_column("alertes", "telephone_contact")
