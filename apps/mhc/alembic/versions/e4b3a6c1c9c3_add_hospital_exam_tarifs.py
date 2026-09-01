"""add hospital exam tarifs table

Revision ID: e4b3a6c1c9c3
Revises: 1d8de8a2f4ce
Create Date: 2025-11-26 15:00:00.000000

If hospitals table is missing (e.g. linear chain without a dedicated migration),
creates it first so the FK from hospital_exam_tarifs can reference it.
"""
from alembic import op
import sqlalchemy as sa


revision = "e4b3a6c1c9c3"
down_revision = "1d8de8a2f4ce"
branch_labels = None
depends_on = None


def _ensure_hospitals_table(conn):
    inspector = sa.inspect(conn)
    if "hospitals" in inspector.get_table_names():
        return
    op.create_table(
        "hospitals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nom", sa.String(200), nullable=False),
        sa.Column("adresse", sa.String(500), nullable=True),
        sa.Column("ville", sa.String(100), nullable=True),
        sa.Column("pays", sa.String(100), nullable=True),
        sa.Column("code_postal", sa.String(20), nullable=True),
        sa.Column("telephone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("latitude", sa.Numeric(10, 8), nullable=False),
        sa.Column("longitude", sa.Numeric(11, 8), nullable=False),
        sa.Column("est_actif", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("specialites", sa.Text(), nullable=True),
        sa.Column("capacite_lits", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hospitals_id", "hospitals", ["id"], unique=False)
    op.create_index("ix_hospitals_nom", "hospitals", ["nom"], unique=False)


def upgrade() -> None:
    conn = op.get_bind()
    # Always ensure hospitals exists first (raw SQL so it runs regardless of file version on server)
    if getattr(conn.dialect, "name", "").startswith("postgresql"):
        conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS hospitals (
                id SERIAL PRIMARY KEY,
                nom VARCHAR(200) NOT NULL,
                adresse VARCHAR(500),
                ville VARCHAR(100),
                pays VARCHAR(100),
                code_postal VARCHAR(20),
                telephone VARCHAR(50),
                email VARCHAR(255),
                latitude NUMERIC(10, 8) NOT NULL DEFAULT 0,
                longitude NUMERIC(11, 8) NOT NULL DEFAULT 0,
                est_actif BOOLEAN NOT NULL DEFAULT true,
                specialites TEXT,
                capacite_lits INTEGER,
                notes TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT now(),
                updated_at TIMESTAMP NOT NULL DEFAULT now()
            )
        """))
        conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_hospitals_id ON hospitals (id)"))
        conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_hospitals_nom ON hospitals (nom)"))
    else:
        inspector = sa.inspect(conn)
        if "hospitals" not in inspector.get_table_names():
            _ensure_hospitals_table(conn)
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


