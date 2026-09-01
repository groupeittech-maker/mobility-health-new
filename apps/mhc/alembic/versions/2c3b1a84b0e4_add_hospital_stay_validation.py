"""Add validation metadata and invoice link to hospital stays

Revision ID: 2c3b1a84b0e4
Revises: 9c2d6c5eaa11
Create Date: 2025-01-24 10:15:00.000000

If invoices table is missing, creates it first so we can add hospital_stay_id.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2c3b1a84b0e4"
down_revision: Union[str, None] = "9c2d6c5eaa11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ensure_invoices_table(conn):
    inspector = sa.inspect(conn)
    if "invoices" in inspector.get_table_names():
        return
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hospital_id", sa.Integer(), nullable=False),
        sa.Column("numero_facture", sa.String(100), nullable=False),
        sa.Column("montant_ht", sa.Numeric(12, 2), nullable=False),
        sa.Column("montant_tva", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("montant_ttc", sa.Numeric(12, 2), nullable=False),
        sa.Column("date_facture", sa.DateTime(), nullable=False),
        sa.Column("date_echeance", sa.DateTime(), nullable=True),
        sa.Column("statut", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("validation_medicale", sa.String(20), nullable=True),
        sa.Column("validation_medicale_par", sa.Integer(), nullable=True),
        sa.Column("validation_medicale_date", sa.DateTime(), nullable=True),
        sa.Column("validation_medicale_notes", sa.Text(), nullable=True),
        sa.Column("validation_sinistre", sa.String(20), nullable=True),
        sa.Column("validation_sinistre_par", sa.Integer(), nullable=True),
        sa.Column("validation_sinistre_date", sa.DateTime(), nullable=True),
        sa.Column("validation_sinistre_notes", sa.Text(), nullable=True),
        sa.Column("validation_compta", sa.String(20), nullable=True),
        sa.Column("validation_compta_par", sa.Integer(), nullable=True),
        sa.Column("validation_compta_date", sa.DateTime(), nullable=True),
        sa.Column("validation_compta_notes", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["hospital_id"], ["hospitals.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["validation_medicale_par"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["validation_sinistre_par"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["validation_compta_par"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("numero_facture"),
    )
    op.create_index("ix_invoices_id", "invoices", ["id"], unique=False)
    op.create_index("ix_invoices_hospital_id", "invoices", ["hospital_id"], unique=False)
    op.create_index("ix_invoices_numero_facture", "invoices", ["numero_facture"], unique=True)
    op.create_index("ix_invoices_statut", "invoices", ["statut"], unique=False)
    op.create_index("ix_invoices_validation_medicale", "invoices", ["validation_medicale"], unique=False)
    op.create_index("ix_invoices_validation_sinistre", "invoices", ["validation_sinistre"], unique=False)
    op.create_index("ix_invoices_validation_compta", "invoices", ["validation_compta"], unique=False)


def upgrade() -> None:
    conn = op.get_bind()
    dialect_name = getattr(conn.dialect, "name", "") or ""
    if "postgresql" in dialect_name:
        conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS invoices (
                id SERIAL PRIMARY KEY,
                hospital_id INTEGER NOT NULL REFERENCES hospitals(id) ON DELETE RESTRICT,
                numero_facture VARCHAR(100) NOT NULL UNIQUE,
                montant_ht NUMERIC(12, 2) NOT NULL,
                montant_tva NUMERIC(12, 2) NOT NULL DEFAULT 0,
                montant_ttc NUMERIC(12, 2) NOT NULL,
                date_facture TIMESTAMP NOT NULL,
                date_echeance TIMESTAMP,
                statut VARCHAR(30) NOT NULL DEFAULT 'draft',
                validation_medicale VARCHAR(20),
                validation_medicale_par INTEGER REFERENCES users(id) ON DELETE SET NULL,
                validation_medicale_date TIMESTAMP,
                validation_medicale_notes TEXT,
                validation_sinistre VARCHAR(20),
                validation_sinistre_par INTEGER REFERENCES users(id) ON DELETE SET NULL,
                validation_sinistre_date TIMESTAMP,
                validation_sinistre_notes TEXT,
                validation_compta VARCHAR(20),
                validation_compta_par INTEGER REFERENCES users(id) ON DELETE SET NULL,
                validation_compta_date TIMESTAMP,
                validation_compta_notes TEXT,
                notes TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT now(),
                updated_at TIMESTAMP NOT NULL DEFAULT now()
            )
        """))
        conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_invoices_hospital_id ON invoices (hospital_id)"))
        conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_invoices_numero_facture ON invoices (numero_facture)"))
        conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_invoices_statut ON invoices (statut)"))
    else:
        _ensure_invoices_table(conn)
    inspector = sa.inspect(conn)
    if "invoices" not in inspector.get_table_names():
        _ensure_invoices_table(conn)
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

    # Only add invoice link if invoices table exists (e.g. created by _ensure_invoices_table above)
    inspector = sa.inspect(op.get_bind())
    if "invoices" in inspector.get_table_names():
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

