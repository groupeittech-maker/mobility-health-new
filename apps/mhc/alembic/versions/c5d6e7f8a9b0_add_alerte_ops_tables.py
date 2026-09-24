"""Tables du centre d'alertes urgence : notes, événements, statut médical.

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
"""
from alembic import op
import sqlalchemy as sa


revision = "c5d6e7f8a9b0"
down_revision = "b4c5d6e7f8a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    pg = conn.dialect.name == "postgresql"
    pk = "SERIAL PRIMARY KEY" if pg else "INTEGER PRIMARY KEY AUTOINCREMENT"
    now = "now()" if pg else "CURRENT_TIMESTAMP"
    json_type = "JSONB" if pg else "TEXT"

    op.execute(sa.text(f"""
        CREATE TABLE IF NOT EXISTS alerte_notes (
            id {pk},
            alerte_id INTEGER NOT NULL REFERENCES alertes(id) ON DELETE CASCADE,
            author_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            author_name VARCHAR(200),
            note TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT {now}
        )
    """))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_alerte_notes_alerte_id ON alerte_notes(alerte_id)"))

    op.execute(sa.text(f"""
        CREATE TABLE IF NOT EXISTS alerte_events (
            id {pk},
            alerte_id INTEGER NOT NULL REFERENCES alertes(id) ON DELETE CASCADE,
            event_type VARCHAR(50) NOT NULL,
            label VARCHAR(300) NOT NULL,
            details {json_type},
            actor_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            actor_name VARCHAR(200),
            created_at TIMESTAMP NOT NULL DEFAULT {now}
        )
    """))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_alerte_events_alerte_id ON alerte_events(alerte_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_alerte_events_created_at ON alerte_events(created_at)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_alerte_events_type ON alerte_events(event_type)"))

    op.execute(sa.text(f"""
        CREATE TABLE IF NOT EXISTS alerte_statuts_medicaux (
            id {pk},
            alerte_id INTEGER NOT NULL UNIQUE REFERENCES alertes(id) ON DELETE CASCADE,
            etat_patient VARCHAR(50),
            motifs_symptomes TEXT,
            besoins_immediats TEXT,
            allergies_connues TEXT,
            traitements_en_cours TEXT,
            updated_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            updated_by_name VARCHAR(200),
            updated_at TIMESTAMP NOT NULL DEFAULT {now}
        )
    """))
    op.execute(sa.text("CREATE UNIQUE INDEX IF NOT EXISTS ix_alerte_statuts_medicaux_alerte_id ON alerte_statuts_medicaux(alerte_id)"))


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS alerte_statuts_medicaux"))
    op.execute(sa.text("DROP TABLE IF EXISTS alerte_events"))
    op.execute(sa.text("DROP TABLE IF EXISTS alerte_notes"))
