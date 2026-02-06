"""add_date_naissance_to_users

Revision ID: e46d145700d0
Revises: 33230b3b5e35
Create Date: 2025-12-02 12:40:21.114937

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e46d145700d0'
down_revision = '33230b3b5e35'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ajouter les colonnes date_naissance, adresse et pays_residence à la table users
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS date_naissance DATE")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS adresse VARCHAR")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS pays_residence VARCHAR")


def downgrade() -> None:
    # Supprimer les colonnes date_naissance, adresse et pays_residence de la table users
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS pays_residence")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS adresse")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS date_naissance")








