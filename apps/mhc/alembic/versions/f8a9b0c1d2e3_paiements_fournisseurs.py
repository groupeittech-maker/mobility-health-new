"""Paiements fournisseurs (flux sortants) + users.reassureur_id.

Revision ID: f8a9b0c1d2e3
Revises: mw1a2b3c4d5e
"""
from alembic import op
import sqlalchemy as sa


revision = "f8a9b0c1d2e3"
down_revision = "mw1a2b3c4d5e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    pg = conn.dialect.name == "postgresql"
    pk = "SERIAL PRIMARY KEY" if pg else "INTEGER PRIMARY KEY AUTOINCREMENT"
    now = "now()" if pg else "CURRENT_TIMESTAMP"

    op.execute(sa.text(f"""
        CREATE TABLE IF NOT EXISTS paiements_fournisseurs (
            id {pk},
            reference VARCHAR(100) NOT NULL UNIQUE,
            type_paiement VARCHAR(50) NOT NULL,
            beneficiaire_type VARCHAR(40) NOT NULL,
            beneficiaire_id INTEGER,
            beneficiaire_nom VARCHAR(200),
            montant NUMERIC(14,2) NOT NULL,
            devise VARCHAR(10) NOT NULL DEFAULT 'XAF',
            periode VARCHAR(20),
            sinistre_id INTEGER REFERENCES sinistres(id) ON DELETE SET NULL,
            souscription_id INTEGER REFERENCES souscriptions(id) ON DELETE SET NULL,
            produit_id INTEGER REFERENCES produits_assurance(id) ON DELETE SET NULL,
            statut VARCHAR(20) NOT NULL DEFAULT 'a_payer',
            description TEXT,
            created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            controlled_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            controlled_at TIMESTAMP,
            paid_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            paid_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT {now}
        )
    """))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_pf_type ON paiements_fournisseurs(type_paiement)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_pf_statut ON paiements_fournisseurs(statut)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_pf_sinistre ON paiements_fournisseurs(sinistre_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_pf_souscription ON paiements_fournisseurs(souscription_id)"))

    # Rattachement d'un compte utilisateur à un réassureur (portail consultation).
    op.execute(sa.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS reassureur_id INTEGER"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_users_reassureur_id ON users(reassureur_id)"))


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE users DROP COLUMN IF EXISTS reassureur_id"))
    op.execute(sa.text("DROP TABLE IF EXISTS paiements_fournisseurs"))
