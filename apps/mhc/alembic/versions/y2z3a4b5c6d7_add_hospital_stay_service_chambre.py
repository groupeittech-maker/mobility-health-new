"""Champs orientation séjour : service et chambre.

Revision ID: y2z3a4b5c6d7
Revises: x1y2z3a4b5c6
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "y2z3a4b5c6d7"
down_revision: Union[str, Sequence[str], None] = "x1y2z3a4b5c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("hospital_stays", sa.Column("service_concerne", sa.String(length=120), nullable=True))
    op.add_column("hospital_stays", sa.Column("chambre", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("hospital_stays", "chambre")
    op.drop_column("hospital_stays", "service_concerne")
