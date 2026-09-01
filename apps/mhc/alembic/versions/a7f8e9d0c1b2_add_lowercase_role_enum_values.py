"""add lowercase role enum values for Python Role enum compatibility

The migration 1d8de8a2f4ce renamed specialized role enum values to UPPERCASE in PostgreSQL,
but the Python app uses lowercase values (e.g. Role.MEDECIN_REFERENT_MH.value = "medecin_referent_mh").
This adds the lowercase values so INSERTs from the API succeed.

Revision ID: a7f8e9d0c1b2
Revises: 1d8de8a2f4ce
Create Date: 2026-02-07

Run this after the uppercase role rename (1d8de8a2f4ce) so the API can insert
lowercase role values. If you see "multiple heads", run:
  alembic upgrade a7f8e9d0c1b2
"""
from alembic import op
import sqlalchemy as sa


revision = "a7f8e9d0c1b2"
down_revision = "1d8de8a2f4ce"
branch_labels = None
depends_on = None

# Lowercase values used by app/core/enums.py Role enum (must exist in PostgreSQL enum)
LOWERCASE_ROLE_VALUES = (
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
    for value in LOWERCASE_ROLE_VALUES:
        op.execute(sa.text(f"ALTER TYPE role ADD VALUE IF NOT EXISTS '{value}'"))


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; downgrade is a no-op.
    # To fully revert, you would need to recreate the type and migrate data.
    pass
