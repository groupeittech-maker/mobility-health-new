"""Add destination_countries and destination_cities tables

Revision ID: add_destinations
Revises: 7c980ad7d503
Create Date: 2025-12-02 19:00:00.000000

Idempotent: skip if tables already exist (e.g. from ad587bb061e5 _ensure_souscriptions_and_deps).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'add_destinations'
down_revision = '7c980ad7d503'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    dialect_name = getattr(conn.dialect, "name", "") or ""
    if "postgresql" in dialect_name:
        # Idempotent: CREATE TABLE IF NOT EXISTS (e.g. tables may exist from ad587bb061e5)
        conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS destination_countries (
                id SERIAL PRIMARY KEY,
                code VARCHAR(10) NOT NULL UNIQUE,
                nom VARCHAR(200) NOT NULL,
                est_actif BOOLEAN NOT NULL DEFAULT true,
                ordre_affichage INTEGER NOT NULL DEFAULT 0,
                notes VARCHAR(500),
                created_at TIMESTAMP NOT NULL DEFAULT now(),
                updated_at TIMESTAMP NOT NULL DEFAULT now()
            )
        """))
        conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_destination_countries_code ON destination_countries (code)"))
        conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_destination_countries_id ON destination_countries (id)"))
        conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_destination_countries_nom ON destination_countries (nom)"))
        conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS destination_cities (
                id SERIAL PRIMARY KEY,
                pays_id INTEGER NOT NULL REFERENCES destination_countries(id) ON DELETE CASCADE,
                nom VARCHAR(200) NOT NULL,
                est_actif BOOLEAN NOT NULL DEFAULT true,
                ordre_affichage INTEGER NOT NULL DEFAULT 0,
                notes VARCHAR(500),
                created_at TIMESTAMP NOT NULL DEFAULT now(),
                updated_at TIMESTAMP NOT NULL DEFAULT now()
            )
        """))
        conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_destination_cities_id ON destination_cities (id)"))
        conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_destination_cities_nom ON destination_cities (nom)"))
        conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_destination_cities_pays_id ON destination_cities (pays_id)"))
        return
    inspector = sa.inspect(conn)
    existing = inspector.get_table_names()
    if "destination_countries" not in existing:
        op.create_table(
            'destination_countries',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('code', sa.String(length=10), nullable=False),
            sa.Column('nom', sa.String(length=200), nullable=False),
            sa.Column('est_actif', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('ordre_affichage', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('notes', sa.String(length=500), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('code')
        )
        op.create_index(op.f('ix_destination_countries_code'), 'destination_countries', ['code'], unique=True)
        op.create_index(op.f('ix_destination_countries_id'), 'destination_countries', ['id'], unique=False)
        op.create_index(op.f('ix_destination_countries_nom'), 'destination_countries', ['nom'], unique=False)
    if "destination_cities" not in existing:
        op.create_table(
            'destination_cities',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('pays_id', sa.Integer(), nullable=False),
            sa.Column('nom', sa.String(length=200), nullable=False),
            sa.Column('est_actif', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('ordre_affichage', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('notes', sa.String(length=500), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['pays_id'], ['destination_countries.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_destination_cities_id'), 'destination_cities', ['id'], unique=False)
        op.create_index(op.f('ix_destination_cities_nom'), 'destination_cities', ['nom'], unique=False)
        op.create_index(op.f('ix_destination_cities_pays_id'), 'destination_cities', ['pays_id'], unique=False)


def downgrade():
    # Supprimer les tables en ordre inverse
    op.drop_index(op.f('ix_destination_cities_pays_id'), table_name='destination_cities')
    op.drop_index(op.f('ix_destination_cities_nom'), table_name='destination_cities')
    op.drop_index(op.f('ix_destination_cities_id'), table_name='destination_cities')
    op.drop_table('destination_cities')
    
    op.drop_index(op.f('ix_destination_countries_nom'), table_name='destination_countries')
    op.drop_index(op.f('ix_destination_countries_id'), table_name='destination_countries')
    op.drop_index(op.f('ix_destination_countries_code'), table_name='destination_countries')
    op.drop_table('destination_countries')

