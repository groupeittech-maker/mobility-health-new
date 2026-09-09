"""Table des avenants de police (suspension / réémission / annulation).

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a8
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a8"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table in inspector.get_table_names()


def upgrade() -> None:
    if _has_table("avenants"):
        return
    op.create_table(
        "avenants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("souscription_id", sa.Integer(), nullable=False),
        sa.Column("type_avenant", sa.String(length=20), nullable=False),
        sa.Column("numero", sa.String(length=120), nullable=False),
        sa.Column("statut", sa.String(length=20), nullable=False, server_default="demande"),
        sa.Column("motifs", sa.JSON(), nullable=True),
        sa.Column("motif_autre", sa.Text(), nullable=True),
        sa.Column("pieces_jointes", sa.JSON(), nullable=True),
        sa.Column("decision_assureur", sa.String(length=20), nullable=True),
        sa.Column("decided_by_id", sa.Integer(), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("date_effet", sa.DateTime(), nullable=True),
        sa.Column("date_echeance", sa.DateTime(), nullable=True),
        sa.Column("parent_avenant_id", sa.Integer(), nullable=True),
        sa.Column("pdf_bucket", sa.String(length=100), nullable=True),
        sa.Column("pdf_path", sa.String(length=500), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["souscription_id"], ["souscriptions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["decided_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_avenant_id"], ["avenants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_avenants_id", "avenants", ["id"])
    op.create_index("ix_avenants_souscription_id", "avenants", ["souscription_id"])
    op.create_index("ix_avenants_type_avenant", "avenants", ["type_avenant"])
    op.create_index("ix_avenants_numero", "avenants", ["numero"], unique=True)
    op.create_index("ix_avenants_statut", "avenants", ["statut"])
    op.create_index("ix_avenants_parent_avenant_id", "avenants", ["parent_avenant_id"])


def downgrade() -> None:
    if not _has_table("avenants"):
        return
    for idx in (
        "ix_avenants_parent_avenant_id",
        "ix_avenants_statut",
        "ix_avenants_numero",
        "ix_avenants_type_avenant",
        "ix_avenants_souscription_id",
        "ix_avenants_id",
    ):
        op.drop_index(idx, table_name="avenants")
    op.drop_table("avenants")
