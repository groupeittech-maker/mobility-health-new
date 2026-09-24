"""Workflow médical : rapports d'étape + assignation/escalade des alertes.

Revision ID: mw1a2b3c4d5e
Revises: d6e7f8a9b0c1
"""
from alembic import op
import sqlalchemy as sa


revision = "mw1a2b3c4d5e"
down_revision = "d6e7f8a9b0c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    pg = conn.dialect.name == "postgresql"
    pk = "SERIAL PRIMARY KEY" if pg else "INTEGER PRIMARY KEY AUTOINCREMENT"
    now = "now()" if pg else "CURRENT_TIMESTAMP"
    json_type = "JSONB" if pg else "TEXT"
    bool_false = "false" if pg else "0"

    op.execute(sa.text(f"""
        CREATE TABLE IF NOT EXISTS hospital_medical_reports (
            id {pk},
            stay_id INTEGER NOT NULL REFERENCES hospital_stays(id) ON DELETE CASCADE,
            report_type VARCHAR(20) NOT NULL DEFAULT 'etape',
            resume TEXT,
            actes {json_type},
            examens {json_type},
            observations TEXT,
            evolution VARCHAR(50),
            created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP NOT NULL DEFAULT {now},
            statut VARCHAR(20) NOT NULL DEFAULT 'soumis',
            validated_mc_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            validated_mc_at TIMESTAMP,
            validated_am_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            validated_am_at TIMESTAMP,
            refusal_reason TEXT,
            escalated BOOLEAN NOT NULL DEFAULT {bool_false}
        )
    """))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_hmr_stay_id ON hospital_medical_reports(stay_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_hmr_statut ON hospital_medical_reports(statut)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_hmr_type ON hospital_medical_reports(report_type)"))

    op.execute(sa.text("ALTER TABLE alertes ADD COLUMN IF NOT EXISTS assigned_role VARCHAR(40)"))
    op.execute(sa.text("ALTER TABLE alertes ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMP"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_alertes_assigned_role ON alertes(assigned_role)"))


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE alertes DROP COLUMN IF EXISTS assigned_role"))
    op.execute(sa.text("ALTER TABLE alertes DROP COLUMN IF EXISTS assigned_at"))
    op.execute(sa.text("DROP TABLE IF EXISTS hospital_medical_reports"))
