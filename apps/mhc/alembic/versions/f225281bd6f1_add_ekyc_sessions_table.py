"""add ekyc_sessions table

Revision ID: f225281bd6f1
Revises: c2d3e4f5a6b7
Create Date: 2026-09-10 00:19:27.775524

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f225281bd6f1'
down_revision = 'c2d3e4f5a6b7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ekyc_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=120), nullable=False),
        sa.Column('customer_reference', sa.String(length=120), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('souscription_id', sa.Integer(), nullable=True),
        sa.Column('flow', sa.String(length=40), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('verification_url', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('identity', sa.JSON(), nullable=True),
        sa.Column('checks', sa.JSON(), nullable=True),
        sa.Column('reasons', sa.JSON(), nullable=True),
        sa.Column('webhook_received_at', sa.DateTime(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['souscription_id'], ['souscriptions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ekyc_sessions_customer_reference'), 'ekyc_sessions', ['customer_reference'], unique=False)
    op.create_index(op.f('ix_ekyc_sessions_id'), 'ekyc_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_ekyc_sessions_session_id'), 'ekyc_sessions', ['session_id'], unique=True)
    op.create_index(op.f('ix_ekyc_sessions_souscription_id'), 'ekyc_sessions', ['souscription_id'], unique=False)
    op.create_index(op.f('ix_ekyc_sessions_status'), 'ekyc_sessions', ['status'], unique=False)
    op.create_index(op.f('ix_ekyc_sessions_user_id'), 'ekyc_sessions', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_ekyc_sessions_user_id'), table_name='ekyc_sessions')
    op.drop_index(op.f('ix_ekyc_sessions_status'), table_name='ekyc_sessions')
    op.drop_index(op.f('ix_ekyc_sessions_souscription_id'), table_name='ekyc_sessions')
    op.drop_index(op.f('ix_ekyc_sessions_session_id'), table_name='ekyc_sessions')
    op.drop_index(op.f('ix_ekyc_sessions_id'), table_name='ekyc_sessions')
    op.drop_index(op.f('ix_ekyc_sessions_customer_reference'), table_name='ekyc_sessions')
    op.drop_table('ekyc_sessions')
