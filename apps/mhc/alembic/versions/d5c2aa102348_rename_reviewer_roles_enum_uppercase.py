"""rename reviewer roles enum uppercase

Revision ID: d5c2aa102348
Revises: c553a5cfbdf9
Create Date: 2025-11-24 08:37:56.098533

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd5c2aa102348'
down_revision = 'c553a5cfbdf9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE role RENAME VALUE 'medical_reviewer' TO 'MEDICAL_REVIEWER';")
    op.execute("ALTER TYPE role RENAME VALUE 'technical_reviewer' TO 'TECHNICAL_REVIEWER';")
    op.execute("ALTER TYPE role RENAME VALUE 'production_agent' TO 'PRODUCTION_AGENT';")


def downgrade() -> None:
    op.execute("ALTER TYPE role RENAME VALUE 'MEDICAL_REVIEWER' TO 'medical_reviewer';")
    op.execute("ALTER TYPE role RENAME VALUE 'TECHNICAL_REVIEWER' TO 'technical_reviewer';")
    op.execute("ALTER TYPE role RENAME VALUE 'PRODUCTION_AGENT' TO 'production_agent';")


