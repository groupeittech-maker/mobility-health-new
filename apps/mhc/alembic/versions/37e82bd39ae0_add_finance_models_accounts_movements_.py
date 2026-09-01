"""Add finance models (accounts, movements, repartitions, refunds)

Revision ID: 37e82bd39ae0
Revises: d103085117c7
Create Date: 2025-11-23 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '37e82bd39ae0'
down_revision = 'd103085117c7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create finance_accounts table
    op.create_table(
        'finance_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_number', sa.String(length=50), nullable=False),
        sa.Column('account_name', sa.String(length=200), nullable=False),
        sa.Column('account_type', sa.String(length=50), nullable=False),
        sa.Column('balance', sa.Numeric(12, 2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_finance_accounts_id'), 'finance_accounts', ['id'], unique=False)
    op.create_index(op.f('ix_finance_accounts_account_number'), 'finance_accounts', ['account_number'], unique=True)
    op.create_index(op.f('ix_finance_accounts_owner_id'), 'finance_accounts', ['owner_id'], unique=False)
    
    # Create finance_movements table
    op.create_table(
        'finance_movements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('movement_type', sa.String(length=50), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('reference', sa.String(length=200), nullable=True),
        sa.Column('reference_type', sa.String(length=50), nullable=True),
        sa.Column('related_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['finance_accounts.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_finance_movements_id'), 'finance_movements', ['id'], unique=False)
    op.create_index(op.f('ix_finance_movements_account_id'), 'finance_movements', ['account_id'], unique=False)
    op.create_index(op.f('ix_finance_movements_movement_type'), 'finance_movements', ['movement_type'], unique=False)
    op.create_index(op.f('ix_finance_movements_reference'), 'finance_movements', ['reference'], unique=False)
    op.create_index(op.f('ix_finance_movements_related_id'), 'finance_movements', ['related_id'], unique=False)
    
    # Create unique index for reference (anti-doublon)
    op.create_index(
        'ix_finance_movements_reference_unique',
        'finance_movements',
        ['reference'],
        unique=True,
        postgresql_where=sa.text('reference IS NOT NULL')
    )
    
    # Create finance_repartitions table
    op.create_table(
        'finance_repartitions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('souscription_id', sa.Integer(), nullable=False),
        sa.Column('paiement_id', sa.Integer(), nullable=False),
        sa.Column('produit_assurance_id', sa.Integer(), nullable=False),
        sa.Column('montant_total', sa.Numeric(12, 2), nullable=False),
        sa.Column('cle_repartition', sa.String(length=50), nullable=False),
        sa.Column('repartition_details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('montant_par_personne', sa.Numeric(12, 2), nullable=True),
        sa.Column('montant_par_groupe', sa.Numeric(12, 2), nullable=True),
        sa.Column('montant_par_duree', sa.Numeric(12, 2), nullable=True),
        sa.Column('montant_par_destination', sa.Numeric(12, 2), nullable=True),
        sa.Column('montant_fixe', sa.Numeric(12, 2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['paiement_id'], ['paiements.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['produit_assurance_id'], ['produits_assurance.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['souscription_id'], ['souscriptions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_finance_repartitions_id'), 'finance_repartitions', ['id'], unique=False)
    op.create_index(op.f('ix_finance_repartitions_souscription_id'), 'finance_repartitions', ['souscription_id'], unique=False)
    op.create_index(op.f('ix_finance_repartitions_paiement_id'), 'finance_repartitions', ['paiement_id'], unique=False)
    op.create_index(op.f('ix_finance_repartitions_produit_assurance_id'), 'finance_repartitions', ['produit_assurance_id'], unique=False)
    
    # Create finance_refunds table
    op.create_table(
        'finance_refunds',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('paiement_id', sa.Integer(), nullable=False),
        sa.Column('souscription_id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('montant', sa.Numeric(12, 2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('statut', sa.String(length=20), nullable=False),
        sa.Column('raison', sa.Text(), nullable=False),
        sa.Column('reference_remboursement', sa.String(length=200), nullable=True),
        sa.Column('date_remboursement', sa.DateTime(), nullable=True),
        sa.Column('processed_by', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['finance_accounts.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['paiement_id'], ['paiements.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['processed_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['souscription_id'], ['souscriptions.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_finance_refunds_id'), 'finance_refunds', ['id'], unique=False)
    op.create_index(op.f('ix_finance_refunds_paiement_id'), 'finance_refunds', ['paiement_id'], unique=False)
    op.create_index(op.f('ix_finance_refunds_souscription_id'), 'finance_refunds', ['souscription_id'], unique=False)
    op.create_index(op.f('ix_finance_refunds_account_id'), 'finance_refunds', ['account_id'], unique=False)
    op.create_index(op.f('ix_finance_refunds_statut'), 'finance_refunds', ['statut'], unique=False)
    op.create_index(op.f('ix_finance_refunds_reference_remboursement'), 'finance_refunds', ['reference_remboursement'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_finance_refunds_reference_remboursement'), table_name='finance_refunds')
    op.drop_index(op.f('ix_finance_refunds_statut'), table_name='finance_refunds')
    op.drop_index(op.f('ix_finance_refunds_account_id'), table_name='finance_refunds')
    op.drop_index(op.f('ix_finance_refunds_souscription_id'), table_name='finance_refunds')
    op.drop_index(op.f('ix_finance_refunds_paiement_id'), table_name='finance_refunds')
    op.drop_index(op.f('ix_finance_refunds_id'), table_name='finance_refunds')
    op.drop_table('finance_refunds')
    
    op.drop_index(op.f('ix_finance_repartitions_produit_assurance_id'), table_name='finance_repartitions')
    op.drop_index(op.f('ix_finance_repartitions_paiement_id'), table_name='finance_repartitions')
    op.drop_index(op.f('ix_finance_repartitions_souscription_id'), table_name='finance_repartitions')
    op.drop_index(op.f('ix_finance_repartitions_id'), table_name='finance_repartitions')
    op.drop_table('finance_repartitions')
    
    op.drop_index('ix_finance_movements_reference_unique', table_name='finance_movements')
    op.drop_index(op.f('ix_finance_movements_related_id'), table_name='finance_movements')
    op.drop_index(op.f('ix_finance_movements_reference'), table_name='finance_movements')
    op.drop_index(op.f('ix_finance_movements_movement_type'), table_name='finance_movements')
    op.drop_index(op.f('ix_finance_movements_account_id'), table_name='finance_movements')
    op.drop_index(op.f('ix_finance_movements_id'), table_name='finance_movements')
    op.drop_table('finance_movements')
    
    op.drop_index(op.f('ix_finance_accounts_owner_id'), table_name='finance_accounts')
    op.drop_index(op.f('ix_finance_accounts_account_number'), table_name='finance_accounts')
    op.drop_index(op.f('ix_finance_accounts_id'), table_name='finance_accounts')
    op.drop_table('finance_accounts')
