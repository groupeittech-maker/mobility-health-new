"""add_user_date_naissance_telephone_sexe

Revision ID: 9e64f032657f
Revises: add_destinations
Create Date: 2025-12-02 19:15:49.345847

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9e64f032657f'
down_revision = 'add_destinations'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ajouter les colonnes date_naissance, telephone, sexe à la table users.
    # Utiliser IF NOT EXISTS car date_naissance peut déjà exister (migration e46d145700d0).
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS date_naissance DATE")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS telephone VARCHAR(20)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS sexe VARCHAR(10)")


def downgrade() -> None:
    # Supprimer les colonnes ajoutées (ne pas supprimer date_naissance si gérée par e46d145700d0)
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS sexe")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS telephone")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS date_naissance")











