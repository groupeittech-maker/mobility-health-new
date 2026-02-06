"""add produit_prime_tarif table

Revision ID: b8c9d0e1f2a3
Revises: merge_commission_contact
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa


revision = 'b8c9d0e1f2a3'
down_revision = 'merge_commission_contact'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'produit_prime_tarif',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('produit_assurance_id', sa.Integer(), nullable=False),
        sa.Column('duree_min_jours', sa.Integer(), nullable=False),
        sa.Column('duree_max_jours', sa.Integer(), nullable=False),
        sa.Column('zone_code', sa.String(50), nullable=True),
        sa.Column('destination_country_id', sa.Integer(), nullable=True),
        sa.Column('age_min', sa.Integer(), nullable=True),
        sa.Column('age_max', sa.Integer(), nullable=True),
        sa.Column('prix', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(10), nullable=True),
        sa.Column('ordre_priorite', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['produit_assurance_id'], ['produits_assurance.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['destination_country_id'], ['destination_countries.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_produit_prime_tarif_produit_assurance_id', 'produit_prime_tarif', ['produit_assurance_id'])
    op.create_index('ix_produit_prime_tarif_zone_code', 'produit_prime_tarif', ['zone_code'])
    op.create_index('ix_produit_prime_tarif_destination_country_id', 'produit_prime_tarif', ['destination_country_id'])


def downgrade() -> None:
    op.drop_index('ix_produit_prime_tarif_destination_country_id', table_name='produit_prime_tarif')
    op.drop_index('ix_produit_prime_tarif_zone_code', table_name='produit_prime_tarif')
    op.drop_index('ix_produit_prime_tarif_produit_assurance_id', table_name='produit_prime_tarif')
    op.drop_table('produit_prime_tarif')
