"""Add assureur_id column to produits_assurance

Revision ID: b6c21f3b0c8d
Revises: 4c7f2e6b5f4a
Create Date: 2025-11-27 22:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b6c21f3b0c8d'
down_revision = '4c7f2e6b5f4a'
branch_labels = None
depends_on = None


def upgrade():
    # Ajouter la colonne assureur_id dans produits_assurance
    op.add_column('produits_assurance',
                  sa.Column('assureur_id', sa.Integer(), sa.ForeignKey('assureurs.id', ondelete='SET NULL'), nullable=True, index=True))


def downgrade():
    # Supprimer la colonne assureur_id en cas de rollback
    op.drop_column('produits_assurance', 'assureur_id')
