"""add hospital foreign key to users

Revision ID: 7b1a1fb6a4f1
Revises: 1f0db8a3b1f5, 52da9ee03d9c
Create Date: 2025-11-26 07:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7b1a1fb6a4f1'
down_revision = ('1f0db8a3b1f5', '52da9ee03d9c')
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('hospital_id', sa.Integer(), nullable=True)
    )
    op.create_index('ix_users_hospital_id', 'users', ['hospital_id'])
    op.create_foreign_key(
        'fk_users_hospital_id_hospitals',
        source_table='users',
        referent_table='hospitals',
        local_cols=['hospital_id'],
        remote_cols=['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_users_hospital_id_hospitals', 'users', type_='foreignkey')
    op.drop_index('ix_users_hospital_id', table_name='users')
    op.drop_column('users', 'hospital_id')

