"""Add tarification_grille_prix (zone x fenetre -> prix ref 18-69)

Revision ID: k7f8g9h0j1k2
Revises: j6e7f8g9h0i1
Create Date: 2026-03-20

"""
from alembic import op
import sqlalchemy as sa


revision = "k7f8g9h0j1k2"
down_revision = "j6e7f8g9h0i1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tarification_grille_prix",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("zone_id", sa.Integer(), nullable=False),
        sa.Column("fenetre_duree_id", sa.Integer(), nullable=False),
        sa.Column("prix", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["fenetre_duree_id"], ["tarification_fenetres_duree.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["zone_id"], ["tarification_zones.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("zone_id", "fenetre_duree_id", name="uq_tarif_grille_zone_fenetre"),
    )
    op.create_index("ix_tarification_grille_prix_zone_id", "tarification_grille_prix", ["zone_id"])
    op.create_index(
        "ix_tarification_grille_prix_fenetre_duree_id",
        "tarification_grille_prix",
        ["fenetre_duree_id"],
    )


def downgrade() -> None:
    op.drop_table("tarification_grille_prix")
