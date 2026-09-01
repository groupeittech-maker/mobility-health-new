"""Add missing typepaiement enum values (CARTE_BANCAIRE, etc.)

Fixes: invalid input value for enum typepaiement: "CARTE_BANCAIRE"
The Python TypePaiement enum uses CARTE_BANCAIRE but the DB had only CARTE_CREDIT.

Revision ID: i5c6d7e8f9g0
Revises: h4c5d6e7f8g9
Create Date: 2025-02-07

"""
from alembic import op
import sqlalchemy as sa


revision = "i5c6d7e8f9g0"
down_revision = "h4c5d6e7f8g9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # Add CARTE_BANCAIRE (Python enum name sent by SQLAlchemy)
    try:
        conn.execute(sa.text("ALTER TYPE typepaiement ADD VALUE IF NOT EXISTS 'CARTE_BANCAIRE'"))
    except Exception:
        pass  # Value may already exist
    # Add other Python TypePaiement enum names used by the application
    for val in ("MOBILE_MONEY_AIRTEL", "MOBILE_MONEY_MTN", "MOBILE_MONEY_ORANGE", "MOBILE_MONEY_MOOV", "PAIEMENT_DIFFERE", "PRELEVEMENT"):
        try:
            conn.execute(sa.text(f"ALTER TYPE typepaiement ADD VALUE IF NOT EXISTS '{val}'"))
        except Exception:
            pass


def downgrade() -> None:
    # PostgreSQL does not support removing enum values
    pass
