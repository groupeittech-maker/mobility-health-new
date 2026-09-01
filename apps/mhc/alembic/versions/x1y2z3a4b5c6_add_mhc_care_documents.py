"""Documents de prise en charge MHC et compteurs de références.

Revision ID: x1y2z3a4b5c6
Revises: w1x2y3z4a5b6
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "x1y2z3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "w1x2y3z4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mhc_reference_counters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("counter_key", sa.String(length=40), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("last_value", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_mhc_reference_counters_counter_key", "mhc_reference_counters", ["counter_key"])
    op.create_index("ix_mhc_reference_counters_year", "mhc_reference_counters", ["year"])
    op.create_unique_constraint(
        "uq_mhc_reference_counters_key_year",
        "mhc_reference_counters",
        ["counter_key", "year"],
    )

    op.create_table(
        "mhc_care_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sinistre_id", sa.Integer(), sa.ForeignKey("sinistres.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_type", sa.String(length=20), nullable=False),
        sa.Column("numero", sa.String(length=120), nullable=False),
        sa.Column("statut", sa.String(length=20), nullable=False, server_default="emi"),
        sa.Column("issued_at", sa.DateTime(), nullable=False),
        sa.Column("valid_until", sa.DateTime(), nullable=True),
        sa.Column("issued_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("parent_document_id", sa.Integer(), sa.ForeignKey("mhc_care_documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("numero"),
    )
    op.create_index("ix_mhc_care_documents_sinistre_id", "mhc_care_documents", ["sinistre_id"])
    op.create_index("ix_mhc_care_documents_document_type", "mhc_care_documents", ["document_type"])
    op.create_index("ix_mhc_care_documents_numero", "mhc_care_documents", ["numero"], unique=True)
    op.create_index("ix_mhc_care_documents_statut", "mhc_care_documents", ["statut"])
    op.create_index("ix_mhc_care_documents_valid_until", "mhc_care_documents", ["valid_until"])
    op.create_index("ix_mhc_care_documents_issued_by_id", "mhc_care_documents", ["issued_by_id"])
    op.create_index("ix_mhc_care_documents_parent_document_id", "mhc_care_documents", ["parent_document_id"])


def downgrade() -> None:
    op.drop_table("mhc_care_documents")
    op.drop_table("mhc_reference_counters")
