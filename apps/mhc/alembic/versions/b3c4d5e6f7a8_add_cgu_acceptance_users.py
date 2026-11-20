"""Trace de l'acceptation des CGU / politique de confidentialité à l'inscription.

Revision ID: b3c4d5e6f7a8
Revises: z9a8b7c6d5e4
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "z9a8b7c6d5e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("cgu_accepte_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("cgu_version", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "cgu_version")
    op.drop_column("users", "cgu_accepte_at")
