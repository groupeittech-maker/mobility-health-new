"""audit_logs: add request_body, response_body, duration_ms, created_at, updated_at

Revision ID: h4c5d6e7f8g9
Revises: g3b4c5d6e7f8
Create Date: 2025-02-07

"""
from alembic import op
import sqlalchemy as sa


revision = "h4c5d6e7f8g9"
down_revision = "g3b4c5d6e7f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent : certaines bases ont déjà ces colonnes sans version Alembic alignée
    op.execute("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS request_body TEXT")
    op.execute("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS response_body TEXT")
    op.execute("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS duration_ms INTEGER")
    op.execute("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS created_at TIMESTAMP")
    op.execute("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP")


def downgrade() -> None:
    op.drop_column("audit_logs", "updated_at")
    op.drop_column("audit_logs", "created_at")
    op.drop_column("audit_logs", "duration_ms")
    op.drop_column("audit_logs", "response_body")
    op.drop_column("audit_logs", "request_body")
