"""Seed de la matrice de permissions par profil dans la table roles.

Revision ID: b4c5d6e7f8a9
Revises: ab12cd34ef56

Insère (ou met à jour) dans `roles` une ligne par profil métier avec son
libellé et sa matrice de permissions JSON (Edition/Contrôle/Consultation),
issue des fichiers FONCTIONNALITES INTERNES / EXTERNE MHC.

Idempotent : INSERT ... ON CONFLICT DO UPDATE (PostgreSQL) ou
INSERT OR REPLACE (SQLite).
"""
import json

from alembic import op
import sqlalchemy as sa


revision = "b4c5d6e7f8a9"
down_revision = "ab12cd34ef56"
branch_labels = None
depends_on = None


def _roles_matrix():
    """Construit la liste (name, description, permissions_json) depuis le module core."""
    from app.core.permissions import ROLE_LABELS, ROLE_PERMISSIONS, permissions_for_role

    rows = []
    for role_key, label in ROLE_LABELS.items():
        rows.append((role_key, label, json.dumps(permissions_for_role(role_key))))
    return rows


def upgrade() -> None:
    conn = op.get_bind()
    rows = _roles_matrix()
    if conn.dialect.name == "postgresql":
        stmt = sa.text("""
            INSERT INTO roles (name, description, permissions, created_at, updated_at)
            VALUES (:name, :description, :permissions, now(), now())
            ON CONFLICT (name) DO UPDATE
            SET description = EXCLUDED.description,
                permissions = EXCLUDED.permissions,
                updated_at = now()
        """)
    else:
        stmt = sa.text("""
            INSERT OR REPLACE INTO roles (name, description, permissions, created_at, updated_at)
            VALUES (:name, :description, :permissions, datetime('now'), datetime('now'))
        """)
    for name, description, permissions in rows:
        conn.execute(stmt, {"name": name, "description": description, "permissions": permissions})


def downgrade() -> None:
    # On conserve les lignes : la matrice est aussi définie dans le code.
    pass
