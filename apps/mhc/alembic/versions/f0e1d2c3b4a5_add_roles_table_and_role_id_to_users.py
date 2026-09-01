"""add roles table and role_id to users

Revision ID: f0e1d2c3b4a5
Revises: 0f5d5cb10850
Create Date: 2025-02-04

Adds the roles table (if missing) and users.role_id so the User model
matches the database. Idempotent: safe to run on DBs that already have
the column or table.
"""
from alembic import op
import sqlalchemy as sa


revision = 'f0e1d2c3b4a5'
down_revision = '0f5d5cb10850'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == 'postgresql':
        # 1) Create roles table if it doesn't exist
        op.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS roles (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                description TEXT,
                permissions TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
                updated_at TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'utc')
            );
        """))
        # 2) Add role_id to users if it doesn't exist
        op.execute(sa.text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'role_id'
                ) THEN
                    ALTER TABLE users ADD COLUMN role_id INTEGER REFERENCES roles(id) ON DELETE SET NULL;
                END IF;
            END $$;
        """))
        # 3) Create index on users.role_id if it doesn't exist
        op.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS ix_users_role_id ON users(role_id);
        """))
    else:
        # SQLite or other: create roles if not exists, add column if not exists
        op.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL UNIQUE,
                description TEXT,
                permissions TEXT,
                created_at DATETIME NOT NULL DEFAULT (datetime('now')),
                updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
            );
        """))
        # SQLite doesn't support IF NOT EXISTS for ADD COLUMN
        try:
            op.execute(sa.text("ALTER TABLE users ADD COLUMN role_id INTEGER REFERENCES roles(id)"))
        except Exception:
            pass  # column already exists


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        op.execute(sa.text("DROP INDEX IF EXISTS ix_users_role_id"))
        op.execute(sa.text("ALTER TABLE users DROP COLUMN IF EXISTS role_id"))
        op.execute(sa.text("DROP TABLE IF EXISTS roles"))
    else:
        # SQLite: no DROP COLUMN IF EXISTS in older versions; skip or use table rebuild
        op.execute(sa.text("DROP TABLE IF EXISTS roles"))
