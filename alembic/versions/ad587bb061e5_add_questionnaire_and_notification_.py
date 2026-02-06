"""add_questionnaire_and_notification_tables

Revision ID: ad587bb061e5
Revises: d103085117c7
Create Date: 2025-11-23 13:44:37.358533

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'ad587bb061e5'
down_revision = 'd103085117c7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create questionnaires table
    op.create_table(
        'questionnaires',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('souscription_id', sa.Integer(), nullable=False),
        sa.Column('type_questionnaire', sa.String(length=20), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('reponses', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('statut', sa.String(length=20), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['souscription_id'], ['souscriptions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_questionnaires_id'), 'questionnaires', ['id'], unique=False)
    op.create_index(op.f('ix_questionnaires_souscription_id'), 'questionnaires', ['souscription_id'], unique=False)
    op.create_index(op.f('ix_questionnaires_type_questionnaire'), 'questionnaires', ['type_questionnaire'], unique=False)
    
    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('type_notification', sa.String(length=50), nullable=False),
        sa.Column('titre', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False),
        sa.Column('lien_relation_id', sa.Integer(), nullable=True),
        sa.Column('lien_relation_type', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)
    op.create_index(op.f('ix_notifications_is_read'), 'notifications', ['is_read'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_notifications_is_read'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_id'), table_name='notifications')
    op.drop_table('notifications')
    
    op.drop_index(op.f('ix_questionnaires_type_questionnaire'), table_name='questionnaires')
    op.drop_index(op.f('ix_questionnaires_souscription_id'), table_name='questionnaires')
    op.drop_index(op.f('ix_questionnaires_id'), table_name='questionnaires')
    op.drop_table('questionnaires')
