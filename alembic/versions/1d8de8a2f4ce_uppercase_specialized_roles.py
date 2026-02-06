"""uppercase specialized operational roles

Revision ID: 1d8de8a2f4ce
Revises: f91b7a4f6e93
Create Date: 2025-11-24 18:05:00.000000
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "1d8de8a2f4ce"
down_revision = "f91b7a4f6e93"
branch_labels = None
depends_on = None

ROLE_RENAMES = (
    ("agent_comptable_mh", "AGENT_COMPTABLE_MH"),
    ("agent_comptable_assureur", "AGENT_COMPTABLE_ASSUREUR"),
    ("agent_comptable_hopital", "AGENT_COMPTABLE_HOPITAL"),
    ("agent_sinistre_mh", "AGENT_SINISTRE_MH"),
    ("agent_sinistre_assureur", "AGENT_SINISTRE_ASSUREUR"),
    ("agent_reception_hopital", "AGENT_RECEPTION_HOPITAL"),
    ("medecin_referent_mh", "MEDECIN_REFERENT_MH"),
    ("medecin_hopital", "MEDECIN_HOPITAL"),
)


def _rename_enum_value(old: str, new: str) -> str:
    return f"""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1
            FROM pg_enum
            JOIN pg_type ON pg_enum.enumtypid = pg_type.oid
            WHERE pg_type.typname = 'role' AND enumlabel = '{old}'
        ) THEN
            ALTER TYPE role RENAME VALUE '{old}' TO '{new}';
        END IF;
    END $$;
    """


def upgrade() -> None:
    for old, new in ROLE_RENAMES:
        op.execute(_rename_enum_value(old, new))


def downgrade() -> None:
    for old, new in reversed(ROLE_RENAMES):
        op.execute(_rename_enum_value(new, old))


















