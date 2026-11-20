"""Workflow sinistre : décision médecin-conseil, blocage et agrément réassureur des factures.

Revision ID: c5d6e7f8a9b0
Revises: b3c4d5e6f7a8
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c5d6e7f8a9b0"
down_revision: Union[str, Sequence[str], None] = "b3c4d5e6f7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Décision de prise en charge (étape 2a/2b) : accord/refus du médecin-conseil
    # enregistré sans émission de bon — le bon 111 est émis par l'agent d'accueil
    # de la clinique à l'acceptation du patient.
    op.add_column(
        "sinistres",
        sa.Column("decision_mc", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "sinistres",
        sa.Column("decision_mc_by_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "sinistres",
        sa.Column("decision_mc_at", sa.DateTime(), nullable=True),
    )
    op.create_foreign_key(
        "fk_sinistres_decision_mc_by_id",
        "sinistres",
        "users",
        ["decision_mc_by_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Factures : blocage du paiement (étape 11 « facture non bloquée ») et
    # agrément du réassureur quand le plafond du produit est dépassé (étape 8).
    op.add_column(
        "invoices",
        sa.Column("bloquee", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "invoices",
        sa.Column("reassureur_agrement", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("invoices", "reassureur_agrement")
    op.drop_column("invoices", "bloquee")
    op.drop_constraint("fk_sinistres_decision_mc_by_id", "sinistres", type_="foreignkey")
    op.drop_column("sinistres", "decision_mc_at")
    op.drop_column("sinistres", "decision_mc_by_id")
    op.drop_column("sinistres", "decision_mc")
