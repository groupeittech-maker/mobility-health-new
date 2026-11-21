"""Ajout du téléphone de contact de l'alerte SOS.

Revision ID: f7a8b9c0d1e2
Revises: g2h3i4j5k6l7
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, Sequence[str], None] = "g2h3i4j5k6l7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("alertes", sa.Column("telephone_contact", sa.String(length=40), nullable=True))


def downgrade() -> None:
    op.drop_column("alertes", "telephone_contact")
