"""Add validation metadata and invoice link to hospital stays

Revision ID: 2c3b1a84b0e4
Revises: 9c2d6c5eaa11
Create Date: 2025-01-24 10:15:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2c3b1a84b0e4"
down_revision: Union[str, None] = "9c2d6c5eaa11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "hospital_stays",
        sa.Column("report_status", sa.String(length=30), nullable=False, server_default="draft"),
    )
    op.add_column(
        "hospital_stays",
        sa.Column("validated_by_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "hospital_stays",
        sa.Column("validated_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "hospital_stays",
        sa.Column("validation_notes", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "fk_hospital_stays_validated_by",
        "hospital_stays",
        "users",
        ["validated_by_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "invoices",
        sa.Column("hospital_stay_id", sa.Integer(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_invoices_hospital_stay_id",
        "invoices",
        ["hospital_stay_id"],
    )
    op.create_foreign_key(
        "fk_invoices_hospital_stay_id",
        "invoices",
        "hospital_stays",
        ["hospital_stay_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.execute("UPDATE hospital_stays SET report_status = 'draft' WHERE report_status IS NULL")
    op.alter_column("hospital_stays", "report_status", server_default=None)


def downgrade() -> None:
    op.drop_constraint("fk_invoices_hospital_stay_id", "invoices", type_="foreignkey")
    op.drop_constraint("uq_invoices_hospital_stay_id", "invoices", type_="unique")
    op.drop_column("invoices", "hospital_stay_id")

    op.drop_constraint("fk_hospital_stays_validated_by", "hospital_stays", type_="foreignkey")
    op.drop_column("hospital_stays", "validation_notes")
    op.drop_column("hospital_stays", "validated_at")
    op.drop_column("hospital_stays", "validated_by_id")
    op.drop_column("hospital_stays", "report_status")

