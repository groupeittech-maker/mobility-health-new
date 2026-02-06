"""add hospital exam tarifs table

Revision ID: e4b3a6c1c9c3
Revises: 1d8de8a2f4ce
Create Date: 2025-11-26 15:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e4b3a6c1c9c3"
down_revision = "1d8de8a2f4ce"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hospital_exam_tarifs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("hospital_id", sa.Integer(), sa.ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nom", sa.String(length=200), nullable=False),
        sa.Column("montant", sa.Numeric(10, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_hospital_exam_tarifs_hospital_id", "hospital_exam_tarifs", ["hospital_id"])
    op.create_unique_constraint(
        "uq_hospital_exam_tarifs_hospital_nom", "hospital_exam_tarifs", ["hospital_id", "nom"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_hospital_exam_tarifs_hospital_nom", "hospital_exam_tarifs", type_="unique")
    op.drop_index("ix_hospital_exam_tarifs_hospital_id", table_name="hospital_exam_tarifs")
    op.drop_table("hospital_exam_tarifs")


