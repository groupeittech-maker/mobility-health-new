"""add users.hospital_id if missing

Revision ID: a0b1c2d3e4f5
Revises: merge_final_2
Create Date: 2025-02-04

Idempotent: adds hospital_id to users only if the column does not exist.
Useful when the DB was migrated via a path that skipped 7b1a1fb6a4f1.
"""
from alembic import op
import sqlalchemy as sa


revision = 'a0b1c2d3e4f5'
down_revision = 'merge_final_2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == 'postgresql':
        op.execute(sa.text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'hospital_id'
                ) THEN
                    ALTER TABLE users ADD COLUMN hospital_id INTEGER REFERENCES hospitals(id) ON DELETE SET NULL;
                END IF;
            END $$;
        """))
        op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_users_hospital_id ON users(hospital_id);"))
    else:
        try:
            op.add_column('users', sa.Column('hospital_id', sa.Integer(), sa.ForeignKey('hospitals.id', ondelete='SET NULL'), nullable=True))
            op.create_index('ix_users_hospital_id', 'users', ['hospital_id'])
        except Exception:
            pass


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        op.execute(sa.text("ALTER TABLE users DROP CONSTRAINT IF EXISTS fk_users_hospital_id_hospitals"))
        op.execute(sa.text("DROP INDEX IF EXISTS ix_users_hospital_id"))
        op.execute(sa.text("ALTER TABLE users DROP COLUMN IF EXISTS hospital_id"))
