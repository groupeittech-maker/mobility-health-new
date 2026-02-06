"""add specialized operational roles

Revision ID: f91b7a4f6e93
Revises: d5c2aa102348
Create Date: 2025-11-24 19:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f91b7a4f6e93'
down_revision = 'd5c2aa102348'
branch_labels = None
depends_on = None

NEW_ROLE_VALUES = (
    "agent_comptable_mh",
    "agent_comptable_assureur",
    "agent_comptable_hopital",
    "agent_sinistre_mh",
    "agent_sinistre_assureur",
    "agent_reception_hopital",
    "medecin_referent_mh",
    "medecin_hopital",
)


def upgrade() -> None:
    for value in NEW_ROLE_VALUES:
        op.execute(
            sa.text(
                f"ALTER TYPE role ADD VALUE IF NOT EXISTS '{value}';"
            )
        )


def downgrade() -> None:
    previous_values = (
        "admin",
        "user",
        "doctor",
        "hospital_admin",
        "finance_manager",
        "sos_operator",
        "medical_reviewer",
        "technical_reviewer",
        "production_agent",
    )

    op.execute("ALTER TYPE role RENAME TO role_old;")
    op.execute(
        "CREATE TYPE role AS ENUM ("
        + ", ".join(f"'{value}'" for value in previous_values)
        + ");"
    )
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE role USING role::text::role;"
    )
    op.execute("DROP TYPE role_old;")

