"""add hospital stays table

Revision ID: 9c2d6c5eaa11
Revises: 8ab2e6ac0bde
Create Date: 2025-11-26 10:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9c2d6c5eaa11'
down_revision = '8ab2e6ac0bde'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'hospital_stays',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sinistre_id', sa.Integer(), nullable=False),
        sa.Column('hospital_id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=True),
        sa.Column('assigned_doctor_id', sa.Integer(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='in_progress'),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('orientation_notes', sa.Text(), nullable=True),
        sa.Column('report_motif_consultation', sa.Text(), nullable=True),
        sa.Column('report_motif_hospitalisation', sa.Text(), nullable=True),
        sa.Column('report_duree_sejour_heures', sa.Integer(), nullable=True),
        sa.Column('report_actes', sa.JSON(), nullable=True),
        sa.Column('report_examens', sa.JSON(), nullable=True),
        sa.Column('report_resume', sa.Text(), nullable=True),
        sa.Column('report_observations', sa.Text(), nullable=True),
        sa.Column('report_submitted_at', sa.DateTime(), nullable=True),
        sa.Column('report_submitted_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['assigned_doctor_id'], ['users.id'], name='fk_hospital_stays_assigned_doctor_id_users', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name='fk_hospital_stays_created_by_id_users', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], name='fk_hospital_stays_hospital_id_hospitals', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['patient_id'], ['users.id'], name='fk_hospital_stays_patient_id_users', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['report_submitted_by'], ['users.id'], name='fk_hospital_stays_report_submitted_by_users', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['sinistre_id'], ['sinistres.id'], name='fk_hospital_stays_sinistre_id_sinistres', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_unique_constraint('uq_hospital_stays_sinistre_id', 'hospital_stays', ['sinistre_id'])
    op.create_index('ix_hospital_stays_hospital_id', 'hospital_stays', ['hospital_id'])
    op.create_index('ix_hospital_stays_status', 'hospital_stays', ['status'])


def downgrade() -> None:
    op.drop_index('ix_hospital_stays_status', table_name='hospital_stays')
    op.drop_index('ix_hospital_stays_hospital_id', table_name='hospital_stays')
    op.drop_constraint('uq_hospital_stays_sinistre_id', 'hospital_stays', type_='unique')
    op.drop_table('hospital_stays')

