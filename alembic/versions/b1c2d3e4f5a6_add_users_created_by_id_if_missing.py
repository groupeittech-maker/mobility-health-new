"""add users.created_by_id if missing

Revision ID: b1c2d3e4f5a6
Revises: a0b1c2d3e4f5
Create Date: 2025-02-04

Idempotent: adds created_by_id to users only if the column does not exist.
"""
from alembic import op
import sqlalchemy as sa


revision = 'b1c2d3e4f5a6'
down_revision = 'a0b1c2d3e4f5'
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
                    WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'created_by_id'
                ) THEN
                    ALTER TABLE users ADD COLUMN created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
                END IF;
            END $$;
        """))
        op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_users_created_by_id ON users(created_by_id);"))
    else:
        try:
            op.add_column('users', sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True))
            op.create_index('ix_users_created_by_id', 'users', ['created_by_id'])
        except Exception:
            pass


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        op.execute(sa.text("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_created_by_id_fkey"))
        op.execute(sa.text("DROP INDEX IF EXISTS ix_users_created_by_id"))
        op.execute(sa.text("ALTER TABLE users DROP COLUMN IF EXISTS created_by_id"))
