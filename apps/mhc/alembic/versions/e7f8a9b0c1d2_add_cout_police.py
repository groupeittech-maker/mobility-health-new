"""add cout_police (forfait MHC) sur parametres pays assureur et souscriptions

Revision ID: e7f8a9b0c1d2
Revises: 673a5e3e15b4
Create Date: 2026-09-12

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e7f8a9b0c1d2"
down_revision = "673a5e3e15b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "parametres_pays_assureur",
        sa.Column("cout_police", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
    )
    op.add_column(
        "souscriptions",
        sa.Column("cout_police", sa.Numeric(precision=12, scale=2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("souscriptions", "cout_police")
    op.drop_column("parametres_pays_assureur", "cout_police")
