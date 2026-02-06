"""add_currency_to_produits_assurance

Revision ID: 33230b3b5e35
Revises: 7c980ad7d503
Create Date: 2025-11-30 01:21:16.047274

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '33230b3b5e35'
down_revision = '7c980ad7d503'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ajouter la colonne currency à la table produits_assurance
    op.execute(
        "ALTER TABLE produits_assurance "
        "ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'XAF'"
    )
    # Mettre à jour les enregistrements existants avec XAF par défaut
    op.execute("UPDATE produits_assurance SET currency = 'XAF' WHERE currency IS NULL")


def downgrade() -> None:
    # Supprimer la colonne currency
    op.execute("ALTER TABLE produits_assurance DROP COLUMN IF EXISTS currency")








