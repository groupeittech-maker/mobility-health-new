"""Add assureur_id column to produits_assurance

Revision ID: b6c21f3b0c8d
Revises: 4c7f2e6b5f4a
Create Date: 2025-11-27 22:10:00.000000

Idempotent: skip if column already exists (e.g. from ad587bb061e5 _ensure_souscriptions_and_deps).
"""

from alembic import op
import sqlalchemy as sa


revision = 'b6c21f3b0c8d'
down_revision = '4c7f2e6b5f4a'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    dialect_name = getattr(conn.dialect, "name", "") or ""
    if "postgresql" in dialect_name:
        # Idempotent: skip if column already exists (e.g. from ad587bb061e5)
        conn.execute(sa.text(
            "ALTER TABLE produits_assurance ADD COLUMN IF NOT EXISTS assureur_id INTEGER REFERENCES assureurs(id) ON DELETE SET NULL"
        ))
        conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_produits_assurance_assureur_id ON produits_assurance (assureur_id)"))
        return
    inspector = sa.inspect(conn)
    cols = [c["name"] for c in inspector.get_columns("produits_assurance")]
    if "assureur_id" in cols:
        return
    op.add_column('produits_assurance',
                  sa.Column('assureur_id', sa.Integer(), sa.ForeignKey('assureurs.id', ondelete='SET NULL'), nullable=True, index=True))


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    cols = [c["name"] for c in inspector.get_columns("produits_assurance")]
    if "assureur_id" not in cols:
        return
    op.drop_column('produits_assurance', 'assureur_id')
