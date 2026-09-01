"""add medecin referent relation to hospitals

Revision ID: 8ab2e6ac0bde
Revises: 7b1a1fb6a4f1
Create Date: 2025-11-26 08:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8ab2e6ac0bde'
down_revision = '7b1a1fb6a4f1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'hospitals',
        sa.Column('medecin_referent_id', sa.Integer(), nullable=True)
    )
    op.create_index(
        'ix_hospitals_medecin_referent_id',
        'hospitals',
        ['medecin_referent_id']
    )
    op.create_foreign_key(
        'fk_hospitals_medecin_referent_id_users',
        source_table='hospitals',
        referent_table='users',
        local_cols=['medecin_referent_id'],
        remote_cols=['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_hospitals_medecin_referent_id_users', 'hospitals', type_='foreignkey')
    op.drop_index('ix_hospitals_medecin_referent_id', table_name='hospitals')
    op.drop_column('hospitals', 'medecin_referent_id')

