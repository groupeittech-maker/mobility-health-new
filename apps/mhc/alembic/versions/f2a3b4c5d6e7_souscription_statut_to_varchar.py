"""souscription statut enum -> varchar

Convertit la colonne souscriptions.statut de l'enum PostgreSQL vers VARCHAR(30)
pour éviter les erreurs InvalidTextRepresentation (app envoie valeurs minuscules).

Revision ID: f2a3b4c5d6e7
Revises: c6f7ab91085a
Create Date: 2025-02-07

"""
from alembic import op
import sqlalchemy as sa


revision = "f2a3b4c5d6e7"
down_revision = "c6f7ab91085a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # 1. Supprimer la valeur par défaut (elle dépend du type enum)
    conn.execute(sa.text("ALTER TABLE souscriptions ALTER COLUMN statut DROP DEFAULT"))
    # 2. Convertir enum -> varchar(30), valeurs en minuscules
    conn.execute(
        sa.text(
            "ALTER TABLE souscriptions "
            "ALTER COLUMN statut TYPE varchar(30) USING lower(statut::text)"
        )
    )
    # 3. Remettre une valeur par défaut en varchar
    conn.execute(sa.text("ALTER TABLE souscriptions ALTER COLUMN statut SET DEFAULT 'en_attente'"))
    # 4. Supprimer l'ancien type enum (plus aucune dépendance)
    conn.execute(sa.text("DROP TYPE IF EXISTS statutsouscription"))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "CREATE TYPE statutsouscription AS ENUM "
            "('en_attente', 'pending', 'active', 'suspendue', 'resiliee', 'expiree')"
        )
    )
    conn.execute(
        sa.text(
            "ALTER TABLE souscriptions "
            "ALTER COLUMN statut TYPE statutsouscription USING statut::statutsouscription"
        )
    )
