"""Add destination_country_id to projets_voyage

Revision ID: a9b8c7d6e5f4
Revises: b8c9d0e1f2a3
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa


revision = 'a9b8c7d6e5f4'
down_revision = 'b8c9d0e1f2a3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE projets_voyage ADD COLUMN IF NOT EXISTS destination_country_id INTEGER")
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_projets_voyage_destination_country_id'
            ) THEN
                ALTER TABLE projets_voyage ADD CONSTRAINT fk_projets_voyage_destination_country_id
                FOREIGN KEY (destination_country_id) REFERENCES destination_countries(id) ON DELETE SET NULL;
            END IF;
        END $$
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_projets_voyage_destination_country_id ON projets_voyage (destination_country_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_projets_voyage_destination_country_id")
    op.execute("ALTER TABLE projets_voyage DROP CONSTRAINT IF EXISTS fk_projets_voyage_destination_country_id")
    op.execute("ALTER TABLE projets_voyage DROP COLUMN IF EXISTS destination_country_id")
