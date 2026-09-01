"""add reviewer roles enum

Revision ID: c553a5cfbdf9
Revises: ef01ea5cc4b2
Create Date: 2025-11-24 08:28:09.989292

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c553a5cfbdf9'
down_revision = 'ef01ea5cc4b2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    new_values = (
        "medical_reviewer",
        "technical_reviewer",
        "production_agent",
    )
    for value in new_values:
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


