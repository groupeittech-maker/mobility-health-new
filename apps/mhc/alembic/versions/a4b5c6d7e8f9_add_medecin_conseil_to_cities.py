"""Associer un médecin-conseil à chaque ville de destination.

Un médecin référent MH est propre à une ou plusieurs villes : la revue
médicale des dossiers est filtrée sur ses villes assignées (ville directe
ou pays dont il est le médecin-conseil, en repli).

Revision ID: e8f9a0b1c2d4
Revises: z3a4b5c6d7e8
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e8f9a0b1c2d4"
down_revision: Union[str, Sequence[str], None] = "z3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "destination_cities",
        sa.Column("medecin_conseil_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_destination_cities_medecin_conseil_id",
        "destination_cities",
        ["medecin_conseil_id"],
    )
    op.create_foreign_key(
        "fk_destination_cities_medecin_conseil_id_users",
        source_table="destination_cities",
        referent_table="users",
        local_cols=["medecin_conseil_id"],
        remote_cols=["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_destination_cities_medecin_conseil_id_users",
        "destination_cities",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_destination_cities_medecin_conseil_id",
        table_name="destination_cities",
    )
    op.drop_column("destination_cities", "medecin_conseil_id")
