"""add rapports table (modèle app.models.rapport.Rapport)

Revision ID: r8a9b0c1d2e3
Revises: p1q2r3s4t5u6
Create Date: 2026-03-29

Idempotent : ne recrée pas la table si elle existe déjà (VPS / BDD partiellement alignée).
"""
from alembic import op
import sqlalchemy as sa


revision = "r8a9b0c1d2e3"
down_revision = "p1q2r3s4t5u6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "rapports" in insp.get_table_names():
        return

    op.create_table(
        "rapports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hospital_id", sa.Integer(), nullable=False),
        sa.Column("sinistre_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("titre", sa.String(length=200), nullable=False),
        sa.Column("type_rapport", sa.String(length=50), nullable=False),
        sa.Column("contenu", sa.Text(), nullable=True),
        sa.Column("fichier_path", sa.String(length=500), nullable=True),
        sa.Column("fichier_nom", sa.String(length=255), nullable=True),
        sa.Column("fichier_taille", sa.Integer(), nullable=True),
        sa.Column("fichier_type", sa.String(length=100), nullable=True),
        sa.Column("est_signe", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("signe_par", sa.Integer(), nullable=True),
        sa.Column("date_signature", sa.DateTime(), nullable=True),
        sa.Column("signature_digitale", sa.Text(), nullable=True),
        sa.Column("statut", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["hospital_id"],
            ["hospitals.id"],
            name="fk_rapports_hospital_id_hospitals",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sinistre_id"],
            ["sinistres.id"],
            name="fk_rapports_sinistre_id_sinistres",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_rapports_user_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["signe_par"],
            ["users.id"],
            name="fk_rapports_signe_par_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rapports_hospital_id"), "rapports", ["hospital_id"], unique=False)
    op.create_index(op.f("ix_rapports_sinistre_id"), "rapports", ["sinistre_id"], unique=False)
    op.create_index(op.f("ix_rapports_user_id"), "rapports", ["user_id"], unique=False)
    op.create_index(op.f("ix_rapports_statut"), "rapports", ["statut"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "rapports" not in insp.get_table_names():
        return

    op.drop_index(op.f("ix_rapports_statut"), table_name="rapports")
    op.drop_index(op.f("ix_rapports_user_id"), table_name="rapports")
    op.drop_index(op.f("ix_rapports_sinistre_id"), table_name="rapports")
    op.drop_index(op.f("ix_rapports_hospital_id"), table_name="rapports")
    op.drop_table("rapports")
