"""Add transaction logs table

Revision ID: d103085117c7
Revises: 994235826591
Create Date: 2025-11-23 13:43:49.037867

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'd103085117c7'
down_revision = '994235826591'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create paiements table first (if it doesn't exist)
    # This table is needed for the foreign key in transaction_logs
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'paiements' not in existing_tables:
        # Create TypePaiement enum (check if it exists first)
        try:
            conn.execute(sa.text("CREATE TYPE typepaiement AS ENUM ('CARTE_CREDIT', 'VIREMENT', 'CHEQUE', 'ESPECES', 'MOBILE_MONEY')"))
        except Exception:
            pass  # Type already exists
        
        # Create StatutPaiement enum (check if it exists first)
        try:
            conn.execute(sa.text("CREATE TYPE statutpaiement AS ENUM ('EN_ATTENTE', 'EN_COURS', 'VALIDE', 'ECHEC', 'ANNULE', 'REMBOURSE')"))
        except Exception:
            pass  # Type already exists
        
        # Create enum objects for use in table definition
        type_paiement_enum = postgresql.ENUM('CARTE_CREDIT', 'VIREMENT', 'CHEQUE', 'ESPECES', 'MOBILE_MONEY', name='typepaiement', create_type=False)
        statut_paiement_enum = postgresql.ENUM('EN_ATTENTE', 'EN_COURS', 'VALIDE', 'ECHEC', 'ANNULE', 'REMBOURSE', name='statutpaiement', create_type=False)
        
        op.create_table(
            'paiements',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('souscription_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('montant', sa.Numeric(10, 2), nullable=False),
            sa.Column('type_paiement', type_paiement_enum, nullable=False),
            sa.Column('statut', statut_paiement_enum, nullable=False),
            sa.Column('date_paiement', sa.DateTime(), nullable=True),
            sa.Column('reference_transaction', sa.String(length=200), nullable=True),
            sa.Column('reference_externe', sa.String(length=200), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('montant_rembourse', sa.Numeric(10, 2), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            # Foreign key to souscriptions will be added later when that table is created
            # sa.ForeignKeyConstraint(['souscription_id'], ['souscriptions.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_paiements_id'), 'paiements', ['id'], unique=False)
        op.create_index(op.f('ix_paiements_souscription_id'), 'paiements', ['souscription_id'], unique=False)
        op.create_index(op.f('ix_paiements_user_id'), 'paiements', ['user_id'], unique=False)
        op.create_index(op.f('ix_paiements_reference_transaction'), 'paiements', ['reference_transaction'], unique=True)
    
    # Create transaction_logs table
    op.create_table(
        'transaction_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('payment_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['payment_id'], ['paiements.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transaction_logs_id'), 'transaction_logs', ['id'], unique=False)
    op.create_index(op.f('ix_transaction_logs_payment_id'), 'transaction_logs', ['payment_id'], unique=False)
    op.create_index(op.f('ix_transaction_logs_user_id'), 'transaction_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_transaction_logs_action'), 'transaction_logs', ['action'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_transaction_logs_action'), table_name='transaction_logs')
    op.drop_index(op.f('ix_transaction_logs_user_id'), table_name='transaction_logs')
    op.drop_index(op.f('ix_transaction_logs_payment_id'), table_name='transaction_logs')
    op.drop_index(op.f('ix_transaction_logs_id'), table_name='transaction_logs')
    op.drop_table('transaction_logs')

