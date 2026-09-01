"""Grille tarifaire finale : zone x fenetre x tranche age -> tarif_final

Revision ID: n9m8k7j6h5g4
Revises: l8g9h0j1k2m3
Create Date: 2026-03-24

"""
from alembic import op
import sqlalchemy as sa


revision = "n9m8k7j6h5g4"
down_revision = "l8g9h0j1k2m3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tarification_grille_finale",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("zone_id", sa.Integer(), nullable=False),
        sa.Column("fenetre_duree_id", sa.Integer(), nullable=False),
        sa.Column("tranche_age_id", sa.Integer(), nullable=False),
        sa.Column("coefficient_age", sa.Numeric(12, 6), nullable=False, server_default="1"),
        sa.Column("tarif_final", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["fenetre_duree_id"], ["tarification_fenetres_duree.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tranche_age_id"], ["tarification_tranches_age.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["zone_id"], ["tarification_zones.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "zone_id",
            "fenetre_duree_id",
            "tranche_age_id",
            name="uq_tarif_grille_finale_zone_fenetre_tranche",
        ),
    )
    op.create_index(
        "ix_tarification_grille_finale_zone_id",
        "tarification_grille_finale",
        ["zone_id"],
    )
    op.create_index(
        "ix_tarification_grille_finale_fenetre_duree_id",
        "tarification_grille_finale",
        ["fenetre_duree_id"],
    )
    op.create_index(
        "ix_tarification_grille_finale_tranche_age_id",
        "tarification_grille_finale",
        ["tranche_age_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_tarification_grille_finale_tranche_age_id", table_name="tarification_grille_finale")
    op.drop_index("ix_tarification_grille_finale_fenetre_duree_id", table_name="tarification_grille_finale")
    op.drop_index("ix_tarification_grille_finale_zone_id", table_name="tarification_grille_finale")
    op.drop_table("tarification_grille_finale")
