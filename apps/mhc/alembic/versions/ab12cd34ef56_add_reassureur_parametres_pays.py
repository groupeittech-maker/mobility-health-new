"""add reassureur (nom + %) sur parametres pays assureur

Revision ID: f1a2b3c4d5e6
Revises: e7f8a9b0c1d2
Create Date: 2026-09-12

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "ab12cd34ef56"
down_revision = "e7f8a9b0c1d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "parametres_pays_assureur",
        sa.Column("reassureur_nom", sa.String(length=200), nullable=False, server_default="SCGRÉ"),
    )
    op.add_column(
        "parametres_pays_assureur",
        sa.Column("reassureur_pct", sa.Numeric(precision=5, scale=2), nullable=False, server_default="10"),
    )


def downgrade() -> None:
    op.drop_column("parametres_pays_assureur", "reassureur_pct")
    op.drop_column("parametres_pays_assureur", "reassureur_nom")
