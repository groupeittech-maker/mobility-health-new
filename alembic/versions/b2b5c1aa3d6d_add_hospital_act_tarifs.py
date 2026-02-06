"""add hospital act tarifs table

Revision ID: b2b5c1aa3d6d
Revises: e4b3a6c1c9c3
Create Date: 2025-11-27 10:15:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b2b5c1aa3d6d"
down_revision = "e4b3a6c1c9c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hospital_act_tarifs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("hospital_id", sa.Integer(), sa.ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=True),
        sa.Column("nom", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
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
    op.create_index("ix_hospital_act_tarifs_hospital_id", "hospital_act_tarifs", ["hospital_id"])
    op.create_index("ix_hospital_act_tarifs_code", "hospital_act_tarifs", ["code"])
    op.create_unique_constraint(
        "uq_hospital_act_tarifs_hospital_nom", "hospital_act_tarifs", ["hospital_id", "nom"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_hospital_act_tarifs_hospital_nom", "hospital_act_tarifs", type_="unique")
    op.drop_index("ix_hospital_act_tarifs_code", table_name="hospital_act_tarifs")
    op.drop_index("ix_hospital_act_tarifs_hospital_id", table_name="hospital_act_tarifs")
    op.drop_table("hospital_act_tarifs")


