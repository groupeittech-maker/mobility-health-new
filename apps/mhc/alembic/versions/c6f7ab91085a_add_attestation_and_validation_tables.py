"""add_attestation_and_validation_tables

Revision ID: c6f7ab91085a
Revises: ad587bb061e5
Create Date: 2025-11-23 20:35:19.892840

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'c6f7ab91085a'
down_revision = 'ad587bb061e5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create attestations table
    op.create_table(
        'attestations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('souscription_id', sa.Integer(), nullable=False),
        sa.Column('paiement_id', sa.Integer(), nullable=True),
        sa.Column('type_attestation', sa.String(length=20), nullable=False),
        sa.Column('numero_attestation', sa.String(length=100), nullable=False),
        sa.Column('chemin_fichier_minio', sa.String(length=500), nullable=False),
        sa.Column('bucket_minio', sa.String(length=100), nullable=False),
        sa.Column('url_signee', sa.Text(), nullable=True),
        sa.Column('date_expiration_url', sa.DateTime(), nullable=True),
        sa.Column('est_valide', sa.Boolean(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['souscription_id'], ['souscriptions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['paiement_id'], ['paiements.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_attestations_id'), 'attestations', ['id'], unique=False)
    op.create_index(op.f('ix_attestations_souscription_id'), 'attestations', ['souscription_id'], unique=False)
    op.create_index(op.f('ix_attestations_paiement_id'), 'attestations', ['paiement_id'], unique=False)
    op.create_index(op.f('ix_attestations_type_attestation'), 'attestations', ['type_attestation'], unique=False)
    op.create_index(op.f('ix_attestations_numero_attestation'), 'attestations', ['numero_attestation'], unique=True)
    
    # Create validations_attestation table
    op.create_table(
        'validations_attestation',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('attestation_id', sa.Integer(), nullable=False),
        sa.Column('type_validation', sa.String(length=20), nullable=False),
        sa.Column('valide_par_user_id', sa.Integer(), nullable=True),
        sa.Column('est_valide', sa.Boolean(), nullable=False),
        sa.Column('date_validation', sa.DateTime(), nullable=True),
        sa.Column('commentaires', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['attestation_id'], ['attestations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['valide_par_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_validations_attestation_id'), 'validations_attestation', ['id'], unique=False)
    op.create_index(op.f('ix_validations_attestation_attestation_id'), 'validations_attestation', ['attestation_id'], unique=False)
    op.create_index(op.f('ix_validations_attestation_type_validation'), 'validations_attestation', ['type_validation'], unique=False)
    op.create_index(op.f('ix_validations_attestation_valide_par_user_id'), 'validations_attestation', ['valide_par_user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_validations_attestation_valide_par_user_id'), table_name='validations_attestation')
    op.drop_index(op.f('ix_validations_attestation_type_validation'), table_name='validations_attestation')
    op.drop_index(op.f('ix_validations_attestation_attestation_id'), table_name='validations_attestation')
    op.drop_index(op.f('ix_validations_attestation_id'), table_name='validations_attestation')
    op.drop_table('validations_attestation')
    
    op.drop_index(op.f('ix_attestations_numero_attestation'), table_name='attestations')
    op.drop_index(op.f('ix_attestations_type_attestation'), table_name='attestations')
    op.drop_index(op.f('ix_attestations_paiement_id'), table_name='attestations')
    op.drop_index(op.f('ix_attestations_souscription_id'), table_name='attestations')
    op.drop_index(op.f('ix_attestations_id'), table_name='attestations')
    op.drop_table('attestations')
