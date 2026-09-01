"""users.role enum -> varchar(30)

Convertit la colonne users.role de l'enum PostgreSQL vers VARCHAR(30)
pour éviter InvalidTextRepresentation (app utilise valeurs minuscules, ex. production_agent).

Revision ID: g3b4c5d6e7f8
Revises: merge_heads_2
Create Date: 2025-02-07

"""
from alembic import op
import sqlalchemy as sa


revision = "g3b4c5d6e7f8"
down_revision = "merge_heads_2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # 1. Supprimer la valeur par défaut (dépend du type enum)
    conn.execute(sa.text("ALTER TABLE users ALTER COLUMN role DROP DEFAULT"))
    # 2. Convertir enum -> varchar(30), valeurs en minuscules
    conn.execute(
        sa.text(
            "ALTER TABLE users "
            "ALTER COLUMN role TYPE varchar(30) USING lower(role::text)"
        )
    )
    # 3. Remettre une valeur par défaut
    conn.execute(sa.text("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'user'"))
    # 4. Supprimer l'ancien type enum (plus utilisé par users.role)
    conn.execute(sa.text("DROP TYPE IF EXISTS role"))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "CREATE TYPE role AS ENUM ("
            "'admin', 'user', 'doctor', 'hospital_admin', 'finance_manager', "
            "'sos_operator', 'medical_reviewer', 'technical_reviewer', 'production_agent', "
            "'agent_comptable_mh', 'agent_comptable_assureur', 'agent_comptable_hopital', "
            "'agent_sinistre_mh', 'agent_sinistre_assureur', 'agent_reception_hopital', "
            "'medecin_referent_mh', 'medecin_hopital'"
            ")"
        )
    )
    conn.execute(
        sa.text(
            "ALTER TABLE users "
            "ALTER COLUMN role TYPE role USING role::role"
        )
    )
