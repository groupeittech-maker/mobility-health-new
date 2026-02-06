"""Add destination_countries and destination_cities tables

Revision ID: add_destinations
Revises: 7c980ad7d503
Create Date: 2025-12-02 19:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_destinations'
down_revision = '7c980ad7d503'  # Dernière migration
branch_labels = None
depends_on = None


def upgrade():
    # Créer la table destination_countries
    op.create_table(
        'destination_countries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=10), nullable=False),
        sa.Column('nom', sa.String(length=200), nullable=False),
        sa.Column('est_actif', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('ordre_affichage', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_destination_countries_code'), 'destination_countries', ['code'], unique=True)
    op.create_index(op.f('ix_destination_countries_id'), 'destination_countries', ['id'], unique=False)
    op.create_index(op.f('ix_destination_countries_nom'), 'destination_countries', ['nom'], unique=False)
    
    # Créer la table destination_cities
    op.create_table(
        'destination_cities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pays_id', sa.Integer(), nullable=False),
        sa.Column('nom', sa.String(length=200), nullable=False),
        sa.Column('est_actif', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('ordre_affichage', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['pays_id'], ['destination_countries.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_destination_cities_id'), 'destination_cities', ['id'], unique=False)
    op.create_index(op.f('ix_destination_cities_nom'), 'destination_cities', ['nom'], unique=False)
    op.create_index(op.f('ix_destination_cities_pays_id'), 'destination_cities', ['pays_id'], unique=False)


def downgrade():
    # Supprimer les tables en ordre inverse
    op.drop_index(op.f('ix_destination_cities_pays_id'), table_name='destination_cities')
    op.drop_index(op.f('ix_destination_cities_nom'), table_name='destination_cities')
    op.drop_index(op.f('ix_destination_cities_id'), table_name='destination_cities')
    op.drop_table('destination_cities')
    
    op.drop_index(op.f('ix_destination_countries_nom'), table_name='destination_countries')
    op.drop_index(op.f('ix_destination_countries_id'), table_name='destination_countries')
    op.drop_index(op.f('ix_destination_countries_code'), table_name='destination_countries')
    op.drop_table('destination_countries')

