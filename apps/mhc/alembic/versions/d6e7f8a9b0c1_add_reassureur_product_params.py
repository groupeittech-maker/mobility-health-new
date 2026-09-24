"""Entité réassureur, surprimes produit et paramètres produit (maquette tarification).

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
"""
from alembic import op
import sqlalchemy as sa


revision = "d6e7f8a9b0c1"
down_revision = "c5d6e7f8a9b0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    pg = conn.dialect.name == "postgresql"
    pk = "SERIAL PRIMARY KEY" if pg else "INTEGER PRIMARY KEY AUTOINCREMENT"
    now = "now()" if pg else "CURRENT_TIMESTAMP"
    updated_at = "TIMESTAMP NOT NULL DEFAULT now()" if pg else "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"
    num52 = "NUMERIC(5,2)"
    num62 = "NUMERIC(6,2)"
    num102 = "NUMERIC(10,2)"

    op.execute(sa.text(f"""
        CREATE TABLE IF NOT EXISTS reassureurs (
            id {pk},
            nom VARCHAR(200) NOT NULL,
            code VARCHAR(50),
            pays VARCHAR(100),
            ville VARCHAR(100),
            adresse VARCHAR(500),
            telephone VARCHAR(50),
            email VARCHAR(255),
            contact_nom VARCHAR(200),
            est_actif BOOLEAN NOT NULL DEFAULT {'true' if pg else '1'},
            cession_defaut_pct {num52},
            commission_cession_defaut_pct {num52},
            created_at {updated_at},
            updated_at {updated_at}
        )
    """))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_reassureurs_nom ON reassureurs(nom)"))
    op.execute(sa.text("CREATE UNIQUE INDEX IF NOT EXISTS ix_reassureurs_code ON reassureurs(code)"))

    op.execute(sa.text(f"""
        CREATE TABLE IF NOT EXISTS produit_surprimes (
            id {pk},
            produit_id INTEGER NOT NULL REFERENCES produits_assurance(id) ON DELETE CASCADE,
            age_min INTEGER NOT NULL,
            age_max INTEGER NOT NULL,
            taux_pct {num62} NOT NULL DEFAULT 0,
            montant_fixe {num102},
            formule VARCHAR(50),
            created_at {updated_at},
            updated_at {updated_at}
        )
    """))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_produit_surprimes_produit_id ON produit_surprimes(produit_id)"))

    new_cols = [
        ("logo_url", "VARCHAR(500)"),
        ("pays", "VARCHAR(100)"),
        ("reassureur_id", "INTEGER"),
        ("retention_assureur_pct", num52),
        ("commission_cession_pct", num52),
        ("cession_reassureur_pct", num52),
        ("cout_police_forfait", num102),
        ("taxe_pct", num52),
        ("taxe_additionnelle_pct", num52),
        ("commission_courtage_pct", num52),
    ]
    for col, typ in new_cols:
        op.execute(sa.text(f"ALTER TABLE produits_assurance ADD COLUMN IF NOT EXISTS {col} {typ}"))
    op.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_produits_assurance_reassureur_id "
        "ON produits_assurance(reassureur_id)"
    ))
    if pg:
        op.execute(sa.text(
            "ALTER TABLE produits_assurance DROP CONSTRAINT IF EXISTS "
            "fk_produits_assurance_reassureur_id"
        ))
        op.execute(sa.text(
            "ALTER TABLE produits_assurance ADD CONSTRAINT "
            "fk_produits_assurance_reassureur_id FOREIGN KEY (reassureur_id) "
            "REFERENCES reassureurs(id) ON DELETE SET NULL"
        ))


def downgrade() -> None:
    for col in [
        "commission_courtage_pct", "taxe_additionnelle_pct", "taxe_pct",
        "cout_police_forfait", "cession_reassureur_pct", "commission_cession_pct",
        "retention_assureur_pct", "reassureur_id", "pays", "logo_url",
    ]:
        op.execute(sa.text(f"ALTER TABLE produits_assurance DROP COLUMN IF EXISTS {col}"))
    op.execute(sa.text("DROP TABLE IF EXISTS produit_surprimes"))
    op.execute(sa.text("DROP TABLE IF EXISTS reassureurs"))
