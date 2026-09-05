"""add sinistre_attachments table

Revision ID: a1b2c3d4e5f7
Revises: z3a4b5c6d7e8
Create Date: 2026-09-05
"""
from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f7"
down_revision = "z3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sinistre_attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sinistre_id", sa.Integer(), nullable=False),
        sa.Column("attachment_type", sa.String(length=50), nullable=False),
        sa.Column("bucket_name", sa.String(length=120), nullable=False),
        sa.Column("object_name", sa.String(length=500), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("uploaded_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["sinistre_id"], ["sinistres.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sinistre_id", "attachment_type", name="uq_sinistre_attachment_type"),
    )
    op.create_index("ix_sinistre_attachments_sinistre_id", "sinistre_attachments", ["sinistre_id"])
    op.create_index("ix_sinistre_attachments_attachment_type", "sinistre_attachments", ["attachment_type"])


def downgrade() -> None:
    op.drop_index("ix_sinistre_attachments_attachment_type", table_name="sinistre_attachments")
    op.drop_index("ix_sinistre_attachments_sinistre_id", table_name="sinistre_attachments")
    op.drop_table("sinistre_attachments")
