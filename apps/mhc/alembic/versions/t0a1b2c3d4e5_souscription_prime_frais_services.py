"""souscriptions: prime_assurance et frais_services (grille voyage)

Revision ID: t0a1b2c3d4e5
Revises: s9b0c1d2e3f4
Create Date: 2026-04-03

"""
from alembic import op
import sqlalchemy as sa


revision = "t0a1b2c3d4e5"
down_revision = "s9b0c1d2e3f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "souscriptions",
        sa.Column("prime_assurance", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "souscriptions",
        sa.Column("frais_services", sa.Numeric(12, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("souscriptions", "frais_services")
    op.drop_column("souscriptions", "prime_assurance")
