"""add courtiers and subscription distribution

Revision ID: v2c3d4e5f6g7
Revises: u1b2c3d4e5f6
Create Date: 2026-04-07 12:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "v2c3d4e5f6g7"
down_revision = "u1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "courtiers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nom", sa.String(length=200), nullable=False),
        sa.Column("pays", sa.String(length=100), nullable=False),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("adresse", sa.String(length=255), nullable=True),
        sa.Column("telephone", sa.String(length=50), nullable=True),
        sa.Column("assureur_id", sa.Integer(), nullable=False),
        sa.Column("commission_pct", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["assureur_id"], ["assureurs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nom"),
    )
    op.create_index(op.f("ix_courtiers_id"), "courtiers", ["id"], unique=False)
    op.create_index(op.f("ix_courtiers_assureur_id"), "courtiers", ["assureur_id"], unique=False)

    op.add_column(
        "souscriptions",
        sa.Column(
            "canal_distribution",
            sa.String(length=20),
            nullable=False,
            server_default="assureur",
        ),
    )
    op.add_column(
        "souscriptions",
        sa.Column("courtier_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f("ix_souscriptions_courtier_id"),
        "souscriptions",
        ["courtier_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_souscriptions_courtier_id",
        "souscriptions",
        "courtiers",
        ["courtier_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_souscriptions_courtier_id", "souscriptions", type_="foreignkey")
    op.drop_index(op.f("ix_souscriptions_courtier_id"), table_name="souscriptions")
    op.drop_column("souscriptions", "courtier_id")
    op.drop_column("souscriptions", "canal_distribution")

    op.drop_index(op.f("ix_courtiers_assureur_id"), table_name="courtiers")
    op.drop_index(op.f("ix_courtiers_id"), table_name="courtiers")
    op.drop_table("courtiers")

