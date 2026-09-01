"""add sinistre process steps table

Revision ID: 1f0db8a3b1f5
Revises: ef01ea5cc4b2
Create Date: 2025-11-24 10:15:00.000000

If sinistres (and alertes) are missing, creates them so sinistre_process_steps FK can reference sinistres.
"""
from alembic import op
import sqlalchemy as sa


revision = '1f0db8a3b1f5'
down_revision = 'ef01ea5cc4b2'
branch_labels = None
depends_on = None


def _ensure_alertes_table(conn):
    inspector = sa.inspect(conn)
    if "alertes" in inspector.get_table_names():
        return
    op.create_table(
        "alertes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("souscription_id", sa.Integer(), nullable=True),
        sa.Column("numero_alerte", sa.String(100), nullable=False),
        sa.Column("latitude", sa.Numeric(10, 8), nullable=False),
        sa.Column("longitude", sa.Numeric(11, 8), nullable=False),
        sa.Column("adresse", sa.String(500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("statut", sa.String(20), nullable=False, server_default="en_attente"),
        sa.Column("priorite", sa.String(20), nullable=False, server_default="normale"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["souscription_id"], ["souscriptions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("numero_alerte"),
    )
    op.create_index("ix_alertes_id", "alertes", ["id"], unique=False)
    op.create_index("ix_alertes_user_id", "alertes", ["user_id"], unique=False)
    op.create_index("ix_alertes_souscription_id", "alertes", ["souscription_id"], unique=False)
    op.create_index("ix_alertes_numero_alerte", "alertes", ["numero_alerte"], unique=True)
    op.create_index("ix_alertes_statut", "alertes", ["statut"], unique=False)


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
        sa.Column("latitude", sa.Numeric(10, 8), nullable=False, server_default="0"),
        sa.Column("longitude", sa.Numeric(11, 8), nullable=False, server_default="0"),
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


def _ensure_sinistres_table(conn):
    inspector = sa.inspect(conn)
    if "sinistres" in inspector.get_table_names():
        return
    op.create_table(
        "sinistres",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("alerte_id", sa.Integer(), nullable=False),
        sa.Column("souscription_id", sa.Integer(), nullable=True),
        sa.Column("hospital_id", sa.Integer(), nullable=True),
        sa.Column("numero_sinistre", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("statut", sa.String(20), nullable=False, server_default="en_cours"),
        sa.Column("agent_sinistre_id", sa.Integer(), nullable=True),
        sa.Column("medecin_referent_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["alerte_id"], ["alertes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["souscription_id"], ["souscriptions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["hospital_id"], ["hospitals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["agent_sinistre_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["medecin_referent_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("numero_sinistre"),
    )
    op.create_index("ix_sinistres_id", "sinistres", ["id"], unique=False)
    op.create_index("ix_sinistres_alerte_id", "sinistres", ["alerte_id"], unique=False)
    op.create_index("ix_sinistres_souscription_id", "sinistres", ["souscription_id"], unique=False)
    op.create_index("ix_sinistres_hospital_id", "sinistres", ["hospital_id"], unique=False)
    op.create_index("ix_sinistres_numero_sinistre", "sinistres", ["numero_sinistre"], unique=True)
    op.create_index("ix_sinistres_statut", "sinistres", ["statut"], unique=False)


def upgrade() -> None:
    conn = op.get_bind()
    dialect_name = getattr(conn.dialect, "name", "") or ""
    if "postgresql" in dialect_name:
        # Ensure hospitals exists first: it has no dedicated migration and is only
        # created defensively by a later revision, so sinistres.hospital_id FK would
        # fail on a clean linear upgrade. IF NOT EXISTS makes this a no-op elsewhere.
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
        # Ensure alertes and sinistres exist (raw SQL so it always runs)
        conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS alertes (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                souscription_id INTEGER REFERENCES souscriptions(id) ON DELETE SET NULL,
                numero_alerte VARCHAR(100) NOT NULL UNIQUE,
                latitude NUMERIC(10, 8) NOT NULL,
                longitude NUMERIC(11, 8) NOT NULL,
                adresse VARCHAR(500),
                description TEXT,
                statut VARCHAR(20) NOT NULL DEFAULT 'en_attente',
                priorite VARCHAR(20) NOT NULL DEFAULT 'normale',
                created_at TIMESTAMP NOT NULL DEFAULT now(),
                updated_at TIMESTAMP NOT NULL DEFAULT now()
            )
        """))
        conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_alertes_user_id ON alertes (user_id)"))
        conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_alertes_souscription_id ON alertes (souscription_id)"))
        conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_alertes_numero_alerte ON alertes (numero_alerte)"))
        conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS sinistres (
                id SERIAL PRIMARY KEY,
                alerte_id INTEGER NOT NULL REFERENCES alertes(id) ON DELETE CASCADE,
                souscription_id INTEGER REFERENCES souscriptions(id) ON DELETE SET NULL,
                hospital_id INTEGER REFERENCES hospitals(id) ON DELETE SET NULL,
                numero_sinistre VARCHAR(100) UNIQUE,
                description TEXT,
                statut VARCHAR(20) NOT NULL DEFAULT 'en_cours',
                agent_sinistre_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                medecin_referent_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                notes TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT now(),
                updated_at TIMESTAMP NOT NULL DEFAULT now()
            )
        """))
        conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_sinistres_alerte_id ON sinistres (alerte_id)"))
        conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_sinistres_souscription_id ON sinistres (souscription_id)"))
        conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_sinistres_hospital_id ON sinistres (hospital_id)"))
    else:
        _ensure_hospitals_table(conn)
        _ensure_alertes_table(conn)
        _ensure_sinistres_table(conn)
    op.create_table(
        'sinistre_process_steps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sinistre_id', sa.Integer(), nullable=False),
        sa.Column('step_key', sa.String(length=64), nullable=False),
        sa.Column('titre', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('ordre', sa.Integer(), nullable=False),
        sa.Column('statut', sa.String(length=20), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('actor_id', sa.Integer(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['sinistre_id'], ['sinistres.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sinistre_process_steps_sinistre_id', 'sinistre_process_steps', ['sinistre_id'])
    op.create_index('ix_sinistre_process_steps_step_key', 'sinistre_process_steps', ['step_key'])
    op.create_index('ix_sinistre_process_steps_statut', 'sinistre_process_steps', ['statut'])


def downgrade() -> None:
    op.drop_index('ix_sinistre_process_steps_statut', table_name='sinistre_process_steps')
    op.drop_index('ix_sinistre_process_steps_step_key', table_name='sinistre_process_steps')
    op.drop_index('ix_sinistre_process_steps_sinistre_id', table_name='sinistre_process_steps')
    op.drop_table('sinistre_process_steps')

















