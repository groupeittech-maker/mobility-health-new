"""Workflow de validation des documents de prise en charge MHC.

Ajoute les colonnes validation_status / validated_at / validations à
mhc_care_documents (colonne « Validé par » du référentiel documentaire).

Revision ID: b1c2d3e4f5a8
Revises: a1b2c3d4e5f7
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b1c2d3e4f5a8"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f7"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(col["name"] == column for col in inspector.get_columns(table))


def upgrade() -> None:
    if not _has_column("mhc_care_documents", "validation_status"):
        op.add_column(
            "mhc_care_documents",
            sa.Column(
                "validation_status",
                sa.String(length=20),
                nullable=False,
                server_default="non_requise",
            ),
        )
        op.create_index(
            "ix_mhc_care_documents_validation_status",
            "mhc_care_documents",
            ["validation_status"],
        )
    if not _has_column("mhc_care_documents", "validated_at"):
        op.add_column(
            "mhc_care_documents",
            sa.Column("validated_at", sa.DateTime(), nullable=True),
        )
    if not _has_column("mhc_care_documents", "validations"):
        op.add_column(
            "mhc_care_documents",
            sa.Column("validations", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    if _has_column("mhc_care_documents", "validations"):
        op.drop_column("mhc_care_documents", "validations")
    if _has_column("mhc_care_documents", "validated_at"):
        op.drop_column("mhc_care_documents", "validated_at")
    if _has_column("mhc_care_documents", "validation_status"):
        op.drop_index(
            "ix_mhc_care_documents_validation_status",
            table_name="mhc_care_documents",
        )
        op.drop_column("mhc_care_documents", "validation_status")
