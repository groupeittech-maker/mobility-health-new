"""add invoice items table

Le modèle ORM InvoiceItem existait sans migration. La table peut déjà
exister sur certaines bases (créée par un script de seed) — la migration
est donc idempotente : elle ne crée la table que si elle est absente.

Revision ID: c6d7e8f9a1b2
Revises: b5c6d7e8f9g0
Create Date: 2026-10-13 07:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c6d7e8f9a1b2"
down_revision: Union[str, Sequence[str], None] = "b5c6d7e8f9g0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "invoice_items" in inspector.get_table_names():
        return

    op.create_table(
        "invoice_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("prestation_id", sa.Integer(), nullable=True),
        sa.Column("libelle", sa.String(length=200), nullable=False),
        sa.Column("quantite", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("prix_unitaire", sa.Numeric(10, 2), nullable=False),
        sa.Column("montant_ht", sa.Numeric(10, 2), nullable=False),
        sa.Column("taux_tva", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("montant_ttc", sa.Numeric(10, 2), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prestation_id"], ["prestations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoice_items_id", "invoice_items", ["id"])
    op.create_index("ix_invoice_items_invoice_id", "invoice_items", ["invoice_id"])
    op.create_index("ix_invoice_items_prestation_id", "invoice_items", ["prestation_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "invoice_items" not in inspector.get_table_names():
        return
    op.drop_index("ix_invoice_items_prestation_id", table_name="invoice_items")
    op.drop_index("ix_invoice_items_invoice_id", table_name="invoice_items")
    op.drop_index("ix_invoice_items_id", table_name="invoice_items")
    op.drop_table("invoice_items")
