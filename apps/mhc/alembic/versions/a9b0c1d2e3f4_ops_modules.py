"""Modules annexes : hôtels, hébergements, transporteurs et missions.

Revision ID: a9b0c1d2e3f4
Revises: f8a9b0c1d2e3
"""
from alembic import op
import sqlalchemy as sa


revision = "a9b0c1d2e3f4"
down_revision = "f8a9b0c1d2e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    pg = conn.dialect.name == "postgresql"
    pk = "SERIAL PRIMARY KEY" if pg else "INTEGER PRIMARY KEY AUTOINCREMENT"
    now = "now()" if pg else "CURRENT_TIMESTAMP"
    b = "true" if pg else "1"

    op.execute(sa.text(f"""
        CREATE TABLE IF NOT EXISTS hotels (
            id {pk},
            nom VARCHAR(200) NOT NULL,
            adresse VARCHAR(500),
            ville VARCHAR(100),
            pays VARCHAR(100),
            telephone VARCHAR(50),
            email VARCHAR(255),
            latitude NUMERIC(10,8),
            longitude NUMERIC(11,8),
            categorie VARCHAR(50),
            contact_nom VARCHAR(200),
            est_actif BOOLEAN NOT NULL DEFAULT {b}
        )
    """))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_hotels_nom ON hotels(nom)"))

    op.execute(sa.text(f"""
        CREATE TABLE IF NOT EXISTS hotel_assignments (
            id {pk},
            alerte_id INTEGER NOT NULL REFERENCES alertes(id) ON DELETE CASCADE,
            hotel_id INTEGER REFERENCES hotels(id) ON DELETE SET NULL,
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            date_arrivee TIMESTAMP,
            date_depart TIMESTAMP,
            nb_nuits INTEGER,
            notes TEXT,
            statut VARCHAR(20) NOT NULL DEFAULT 'reserve',
            created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP NOT NULL DEFAULT {now}
        )
    """))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_hotel_assignments_alerte ON hotel_assignments(alerte_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_hotel_assignments_statut ON hotel_assignments(statut)"))

    op.execute(sa.text(f"""
        CREATE TABLE IF NOT EXISTS transport_providers (
            id {pk},
            nom VARCHAR(200) NOT NULL,
            type_vehicule VARCHAR(80),
            ville VARCHAR(100),
            pays VARCHAR(100),
            telephone VARCHAR(50),
            email VARCHAR(255),
            contact_nom VARCHAR(200),
            est_actif BOOLEAN NOT NULL DEFAULT {b}
        )
    """))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_transport_providers_nom ON transport_providers(nom)"))

    op.execute(sa.text(f"""
        CREATE TABLE IF NOT EXISTS transport_missions (
            id {pk},
            sinistre_id INTEGER NOT NULL REFERENCES sinistres(id) ON DELETE CASCADE,
            provider_id INTEGER REFERENCES transport_providers(id) ON DELETE SET NULL,
            type_transport VARCHAR(80),
            depart VARCHAR(300),
            arrivee VARCHAR(300),
            date_mission TIMESTAMP,
            statut VARCHAR(20) NOT NULL DEFAULT 'demandee',
            notes TEXT,
            created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP NOT NULL DEFAULT {now}
        )
    """))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_transport_missions_sinistre ON transport_missions(sinistre_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_transport_missions_statut ON transport_missions(statut)"))


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS transport_missions"))
    op.execute(sa.text("DROP TABLE IF EXISTS transport_providers"))
    op.execute(sa.text("DROP TABLE IF EXISTS hotel_assignments"))
    op.execute(sa.text("DROP TABLE IF EXISTS hotels"))
