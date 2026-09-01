"""add_resiliation_fields_to_subscriptions

Revision ID: a45f38567462
Revises: 9e64f032657f
Create Date: 2025-12-03 11:49:18.063604

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a45f38567462'
down_revision = '9e64f032657f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Colonnes et index en IF NOT EXISTS pour éviter DuplicateColumn si déjà appliqué (ex. autre branche)
    op.execute("ALTER TABLE souscriptions ADD COLUMN IF NOT EXISTS demande_resiliation VARCHAR(20)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_souscriptions_demande_resiliation ON souscriptions (demande_resiliation)")
    op.execute("ALTER TABLE souscriptions ADD COLUMN IF NOT EXISTS demande_resiliation_date TIMESTAMP")
    op.execute("ALTER TABLE souscriptions ADD COLUMN IF NOT EXISTS demande_resiliation_notes TEXT")
    op.execute("ALTER TABLE souscriptions ADD COLUMN IF NOT EXISTS demande_resiliation_par_agent INTEGER")
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_souscriptions_demande_resiliation_par_agent'
            ) THEN
                ALTER TABLE souscriptions
                ADD CONSTRAINT fk_souscriptions_demande_resiliation_par_agent
                FOREIGN KEY (demande_resiliation_par_agent) REFERENCES users(id) ON DELETE SET NULL;
            END IF;
        END $$
    """)
    op.execute("ALTER TABLE souscriptions ADD COLUMN IF NOT EXISTS demande_resiliation_date_traitement TIMESTAMP")


def downgrade() -> None:
    op.execute("ALTER TABLE souscriptions DROP COLUMN IF EXISTS demande_resiliation_date_traitement")
    op.execute("ALTER TABLE souscriptions DROP CONSTRAINT IF EXISTS fk_souscriptions_demande_resiliation_par_agent")
    op.execute("ALTER TABLE souscriptions DROP COLUMN IF EXISTS demande_resiliation_par_agent")
    op.execute("ALTER TABLE souscriptions DROP COLUMN IF EXISTS demande_resiliation_notes")
    op.execute("ALTER TABLE souscriptions DROP COLUMN IF EXISTS demande_resiliation_date")
    op.execute("DROP INDEX IF EXISTS ix_souscriptions_demande_resiliation")
    op.execute("ALTER TABLE souscriptions DROP COLUMN IF EXISTS demande_resiliation")













