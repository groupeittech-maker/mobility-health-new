"""Add product-level age surcharge percentages (legacy matrix tarifs).

Révision : k7f8g9h0j1k2 -> l8g9h0j1k2m3
"""
from alembic import op
import sqlalchemy as sa


revision = "l8g9h0j1k2m3"
down_revision = "k7f8g9h0j1k2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "produits_assurance",
        sa.Column(
            "surprime_moins_18_pct",
            sa.Numeric(6, 2),
            nullable=True,
            server_default="0",
        ),
    )
    op.add_column(
        "produits_assurance",
        sa.Column(
            "surprime_70_75_pct",
            sa.Numeric(6, 2),
            nullable=True,
            server_default="0",
        ),
    )
    op.add_column(
        "produits_assurance",
        sa.Column(
            "surprime_76_80_pct",
            sa.Numeric(6, 2),
            nullable=True,
            server_default="0",
        ),
    )
    op.add_column(
        "produits_assurance",
        sa.Column(
            "surprime_81_89_pct",
            sa.Numeric(6, 2),
            nullable=True,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("produits_assurance", "surprime_81_89_pct")
    op.drop_column("produits_assurance", "surprime_76_80_pct")
    op.drop_column("produits_assurance", "surprime_70_75_pct")
    op.drop_column("produits_assurance", "surprime_moins_18_pct")
