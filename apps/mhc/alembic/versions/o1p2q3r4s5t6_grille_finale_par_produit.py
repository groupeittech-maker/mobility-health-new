"""Grille finale : rattachement optionnel au produit (global repli)

Revision ID: o1p2q3r4s5t6
Revises: n9m8k7j6h5g4
Create Date: 2026-03-24

"""
from alembic import op
import sqlalchemy as sa


revision = "o1p2q3r4s5t6"
down_revision = "n9m8k7j6h5g4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tarification_grille_finale",
        sa.Column("produit_assurance_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_tarif_grille_finale_produit",
        "tarification_grille_finale",
        "produits_assurance",
        ["produit_assurance_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(
        "uq_tarif_grille_finale_zone_fenetre_tranche",
        "tarification_grille_finale",
        type_="unique",
    )
    op.create_index(
        "ix_tarification_grille_finale_produit_assurance_id",
        "tarification_grille_finale",
        ["produit_assurance_id"],
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_tarif_grille_finale_global
        ON tarification_grille_finale (zone_id, fenetre_duree_id, tranche_age_id)
        WHERE produit_assurance_id IS NULL;
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_tarif_grille_finale_par_produit
        ON tarification_grille_finale (produit_assurance_id, zone_id, fenetre_duree_id, tranche_age_id)
        WHERE produit_assurance_id IS NOT NULL;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_tarif_grille_finale_par_produit")
    op.execute("DROP INDEX IF EXISTS uq_tarif_grille_finale_global")
    op.drop_index(
        "ix_tarification_grille_finale_produit_assurance_id",
        table_name="tarification_grille_finale",
    )
    op.drop_constraint(
        "fk_tarif_grille_finale_produit",
        "tarification_grille_finale",
        type_="foreignkey",
    )
    op.drop_column("tarification_grille_finale", "produit_assurance_id")
    op.create_unique_constraint(
        "uq_tarif_grille_finale_zone_fenetre_tranche",
        "tarification_grille_finale",
        ["zone_id", "fenetre_duree_id", "tranche_age_id"],
    )
