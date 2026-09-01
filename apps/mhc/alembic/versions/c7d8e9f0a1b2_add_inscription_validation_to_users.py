"""add inscription validation and email_verified to users

Workflow: inscription (register) -> médecin MH valide -> abonné peut se connecter pour souscrire.
"""
from alembic import op
import sqlalchemy as sa


revision = 'c7d8e9f0a1b2'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS validation_inscription VARCHAR(20)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS validation_inscription_par INTEGER")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS validation_inscription_date TIMESTAMP")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS validation_inscription_notes TEXT")
    # Utilisateurs existants : considérés comme vérifiés et inscription approuvée (rétrocompatibilité)
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        conn.execute(sa.text(
            "UPDATE users SET email_verified = TRUE, validation_inscription = 'approved' WHERE email_verified IS NULL"
        ))
    else:
        conn.execute(sa.text(
            "UPDATE users SET email_verified = 1, validation_inscription = 'approved' WHERE email_verified IS NULL"
        ))
    op.execute("ALTER TABLE users ALTER COLUMN email_verified SET DEFAULT false")
    op.execute("ALTER TABLE users ALTER COLUMN email_verified SET NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_validation_inscription ON users (validation_inscription)")
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_users_validation_inscription_par_users'
            ) THEN
                ALTER TABLE users ADD CONSTRAINT fk_users_validation_inscription_par_users
                FOREIGN KEY (validation_inscription_par) REFERENCES users(id) ON DELETE SET NULL;
            END IF;
        END $$
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS fk_users_validation_inscription_par_users")
    op.execute("DROP INDEX IF EXISTS ix_users_validation_inscription")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS validation_inscription_notes")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS validation_inscription_date")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS validation_inscription_par")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS validation_inscription")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS email_verified")
