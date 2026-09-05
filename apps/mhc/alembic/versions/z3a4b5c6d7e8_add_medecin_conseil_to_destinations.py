"""Associer un médecin-conseil à chaque pays de destination.

Revision ID: z3a4b5c6d7e8
Revises: y2z3a4b5c6d7
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "z3a4b5c6d7e8"
down_revision: Union[str, Sequence[str], None] = "y2z3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "destination_countries",
        sa.Column("medecin_conseil_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_destination_countries_medecin_conseil_id",
        "destination_countries",
        ["medecin_conseil_id"],
    )
    op.create_foreign_key(
        "fk_destination_countries_medecin_conseil_id_users",
        source_table="destination_countries",
        referent_table="users",
        local_cols=["medecin_conseil_id"],
        remote_cols=["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_destination_countries_medecin_conseil_id_users",
        "destination_countries",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_destination_countries_medecin_conseil_id",
        table_name="destination_countries",
    )
    op.drop_column("destination_countries", "medecin_conseil_id")
