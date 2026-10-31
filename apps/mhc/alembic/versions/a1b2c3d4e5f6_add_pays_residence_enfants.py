"""Ajout du pays de résidence sur les enfants bénéficiaires + merge des branches.

Revision ID: a1b2c3d4e5f6
Revises: e8f9a0b1c2d4, b5c6d7e8f9a0, c6d7e8f9a1b2, e9f0a1b2c3d5
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = (
    "e8f9a0b1c2d4",
    "b5c6d7e8f9a0",
    "c6d7e8f9a1b2",
    "e9f0a1b2c3d5",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "enfants_beneficiaires",
        sa.Column("pays_residence", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("enfants_beneficiaires", "pays_residence")
