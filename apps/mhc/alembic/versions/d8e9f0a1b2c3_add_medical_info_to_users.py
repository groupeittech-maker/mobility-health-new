"""add medical info at registration (maladies_chroniques, traitements, antecedents, grossesse)

Informations médicales recueillies à l'inscription pour validation par le médecin MH.
"""
from alembic import op
import sqlalchemy as sa


revision = 'd8e9f0a1b2c3'
down_revision = 'c7d8e9f0a1b2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS maladies_chroniques TEXT")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS traitements_en_cours TEXT")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS antecedents_recents TEXT")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS grossesse BOOLEAN")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS grossesse")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS antecedents_recents")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS traitements_en_cours")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS maladies_chroniques")
