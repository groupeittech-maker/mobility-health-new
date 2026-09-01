"""tarification_zone_pays : un pays peut appartenir à plusieurs zones (ex. INTRA + INTER).

Remplace la contrainte unique sur destination_country_id par (zone_id, destination_country_id).

Revision ID: u1b2c3d4e5f6
Revises: t0a1b2c3d4e5
Create Date: 2026-04-04

"""
from alembic import op


revision = "u1b2c3d4e5f6"
down_revision = "t0a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_tarif_zone_pays_country", "tarification_zone_pays", type_="unique")
    op.create_unique_constraint(
        "uq_tarif_zone_pays_zone_country",
        "tarification_zone_pays",
        ["zone_id", "destination_country_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_tarif_zone_pays_zone_country", "tarification_zone_pays", type_="unique")
    op.create_unique_constraint(
        "uq_tarif_zone_pays_country",
        "tarification_zone_pays",
        ["destination_country_id"],
    )
