"""add_created_by_id_to_users

Revision ID: 7c980ad7d503
Revises: 0d2e6a1b8c34
Create Date: 2025-11-28 17:59:39.390967

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7c980ad7d503'
down_revision = '0d2e6a1b8c34'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Vérifier si la colonne existe déjà avant de l'ajouter
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    if 'created_by_id' not in columns:
        # Ajouter la colonne created_by_id à la table users
        op.add_column(
            'users',
            sa.Column('created_by_id', sa.Integer(), nullable=True)
        )
    
    # Vérifier si l'index existe déjà
    indexes = [idx['name'] for idx in inspector.get_indexes('users')]
    if 'ix_users_created_by_id' not in indexes:
        # Créer l'index pour améliorer les performances des requêtes
        op.create_index(
            op.f('ix_users_created_by_id'),
            'users',
            ['created_by_id'],
            unique=False
        )
    
    # Vérifier si la contrainte existe déjà
    foreign_keys = [fk['name'] for fk in inspector.get_foreign_keys('users')]
    if 'fk_users_created_by_id_users' not in foreign_keys:
        # Créer la contrainte de clé étrangère
        op.create_foreign_key(
            'fk_users_created_by_id_users',
            'users',
            'users',
            ['created_by_id'],
            ['id'],
            ondelete='SET NULL'
        )


def downgrade() -> None:
    # Supprimer la contrainte de clé étrangère
    op.drop_constraint('fk_users_created_by_id_users', 'users', type_='foreignkey')
    
    # Supprimer l'index
    op.drop_index(op.f('ix_users_created_by_id'), table_name='users')
    
    # Supprimer la colonne
    op.drop_column('users', 'created_by_id')






