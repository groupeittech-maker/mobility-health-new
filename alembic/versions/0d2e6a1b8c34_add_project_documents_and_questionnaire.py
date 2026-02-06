"""Add project documents and questionnaire preference

Revision ID: 0d2e6a1b8c34
Revises: 59835e3cda33
Create Date: 2025-11-28 10:30:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0d2e6a1b8c34"
down_revision = "59835e3cda33"
branch_labels = None
depends_on = None

QUESTIONNAIRE_ENUM_NAME = "questionnairetype"


def upgrade() -> None:
    questionnaire_enum = sa.Enum("short", "long", name=QUESTIONNAIRE_ENUM_NAME)
    bind = op.get_bind()
    questionnaire_enum.create(bind, checkfirst=True)

    op.add_column(
        "projets_voyage",
        sa.Column(
            "questionnaire_type",
            questionnaire_enum,
            nullable=False,
            server_default="long",
        ),
    )
    op.alter_column(
        "projets_voyage",
        "questionnaire_type",
        server_default=None,
    )

    op.create_table(
        "projet_voyage_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("projet_voyage_id", sa.Integer(), nullable=False),
        sa.Column("doc_type", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("bucket_name", sa.String(length=63), nullable=False),
        sa.Column("object_name", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("minio_etag", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["projet_voyage_id"],
            ["projets_voyage.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_projet_voyage_documents_id"),
        "projet_voyage_documents",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_projet_voyage_documents_projet_voyage_id"),
        "projet_voyage_documents",
        ["projet_voyage_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_projet_voyage_documents_doc_type"),
        "projet_voyage_documents",
        ["doc_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_projet_voyage_documents_doc_type"),
        table_name="projet_voyage_documents",
    )
    op.drop_index(
        op.f("ix_projet_voyage_documents_projet_voyage_id"),
        table_name="projet_voyage_documents",
    )
    op.drop_index(
        op.f("ix_projet_voyage_documents_id"),
        table_name="projet_voyage_documents",
    )
    op.drop_table("projet_voyage_documents")

    op.drop_column("projets_voyage", "questionnaire_type")

    questionnaire_enum = sa.Enum("short", "long", name=QUESTIONNAIRE_ENUM_NAME)
    bind = op.get_bind()
    questionnaire_enum.drop(bind, checkfirst=True)















