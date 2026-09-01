"""Add tarification zones, duration windows, age brackets (coefficients)

Revision ID: j6e7f8g9h0i1
Revises: i5c6d7e8f9g0
Create Date: 2026-03-20

"""
from alembic import op
import sqlalchemy as sa


revision = "j6e7f8g9h0i1"
down_revision = "i5c6d7e8f9g0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tarification_zones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("nom", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("coefficient", sa.Numeric(12, 6), nullable=False, server_default="1"),
        sa.Column("ordre_affichage", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("est_actif", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tarification_zones_code", "tarification_zones", ["code"], unique=True)

    op.create_table(
        "tarification_zone_pays",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("zone_id", sa.Integer(), nullable=False),
        sa.Column("destination_country_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["destination_country_id"], ["destination_countries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["zone_id"], ["tarification_zones.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("destination_country_id", name="uq_tarif_zone_pays_country"),
    )
    op.create_index("ix_tarification_zone_pays_zone_id", "tarification_zone_pays", ["zone_id"])
    op.create_index(
        "ix_tarification_zone_pays_destination_country_id",
        "tarification_zone_pays",
        ["destination_country_id"],
    )

    op.create_table(
        "tarification_fenetres_duree",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("libelle", sa.String(length=200), nullable=True),
        sa.Column("duree_min_jours", sa.Integer(), nullable=False),
        sa.Column("duree_max_jours", sa.Integer(), nullable=False),
        sa.Column("coefficient", sa.Numeric(12, 6), nullable=False, server_default="1"),
        sa.Column("ordre_priorite", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("est_actif", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "tarification_tranches_age",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("libelle", sa.String(length=200), nullable=True),
        sa.Column("age_min", sa.Integer(), nullable=True),
        sa.Column("age_max", sa.Integer(), nullable=True),
        sa.Column("coefficient", sa.Numeric(12, 6), nullable=False, server_default="1"),
        sa.Column("ordre_priorite", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("est_actif", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("tarification_tranches_age")
    op.drop_table("tarification_fenetres_duree")
    op.drop_table("tarification_zone_pays")
    op.drop_index("ix_tarification_zones_code", table_name="tarification_zones")
    op.drop_table("tarification_zones")
