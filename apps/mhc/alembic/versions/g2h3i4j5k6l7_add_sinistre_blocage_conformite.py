"""Blocage conformité des sinistres (bloque, motif, auteur, date).

Revision ID: g2h3i4j5k6l7
Revises: d0e1f2a3b4c5
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "g2h3i4j5k6l7"
down_revision: Union[str, Sequence[str], None] = "d0e1f2a3b4c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sinistres",
        sa.Column("bloque", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "sinistres",
        sa.Column("motif_blocage", sa.Text(), nullable=True),
    )
    op.add_column(
        "sinistres",
        sa.Column("bloque_par", sa.Integer(), nullable=True),
    )
    op.add_column(
        "sinistres",
        sa.Column("bloque_le", sa.DateTime(), nullable=True),
    )
    op.create_foreign_key(
        "fk_sinistres_bloque_par",
        "sinistres",
        "users",
        ["bloque_par"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_sinistres_bloque_par", "sinistres", type_="foreignkey")
    op.drop_column("sinistres", "bloque_le")
    op.drop_column("sinistres", "bloque_par")
    op.drop_column("sinistres", "motif_blocage")
    op.drop_column("sinistres", "bloque")
