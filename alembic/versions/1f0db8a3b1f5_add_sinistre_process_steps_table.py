"""add sinistre process steps table

Revision ID: 1f0db8a3b1f5
Revises: ef01ea5cc4b2
Create Date: 2025-11-24 10:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1f0db8a3b1f5'
down_revision = 'ef01ea5cc4b2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'sinistre_process_steps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sinistre_id', sa.Integer(), nullable=False),
        sa.Column('step_key', sa.String(length=64), nullable=False),
        sa.Column('titre', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('ordre', sa.Integer(), nullable=False),
        sa.Column('statut', sa.String(length=20), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('actor_id', sa.Integer(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['sinistre_id'], ['sinistres.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sinistre_process_steps_sinistre_id', 'sinistre_process_steps', ['sinistre_id'])
    op.create_index('ix_sinistre_process_steps_step_key', 'sinistre_process_steps', ['step_key'])
    op.create_index('ix_sinistre_process_steps_statut', 'sinistre_process_steps', ['statut'])


def downgrade() -> None:
    op.drop_index('ix_sinistre_process_steps_statut', table_name='sinistre_process_steps')
    op.drop_index('ix_sinistre_process_steps_step_key', table_name='sinistre_process_steps')
    op.drop_index('ix_sinistre_process_steps_sinistre_id', table_name='sinistre_process_steps')
    op.drop_table('sinistre_process_steps')

















