#!/usr/bin/env python3
"""
Script pour rendre idempotentes les migrations Alembic sur le serveur.
Évite les erreurs DuplicateColumn / UndefinedTable quand plusieurs branches
ont été fusionnées ou que l'ordre d'exécution varie.

Migrations corrigées par ce script (ADD COLUMN IF NOT EXISTS / DROP IF EXISTS) :
  - 9e64f032657f : users (date_naissance, telephone, sexe)
  - a45f38567462 : souscriptions (demande_resiliation, etc.)
  - b2c3d4e5f6a7 : produits_assurance (primes_generees)
  - a1b2c3d4e5f6 : users (nationalite, numero_passeport, validite_passeport, contact_urgence)
  - e5f6a7b8c9d0 : users (nom_contact_urgence)
  - d8e9f0a1b2c3 : users (maladies_chroniques, traitements_en_cours, antecedents_recents, grossesse)
  - c7d8e9f0a1b2 : users (email_verified, validation_inscription, etc.)
  - a9b8c7d6e5f4 : projets_voyage (destination_country_id)

La migration add_ia_analysis_tables.py (table questionnaires si manquante) est déjà
corrigée dans le dépôt ; déployer le code (git pull) pour l'avoir sur le serveur.

À exécuter à la racine du projet (où se trouve alembic/versions/) :
  python3 scripts/fix_alembic_idempotent_migrations.py

Puis lancer : sudo docker compose exec api alembic upgrade head
"""

import os
import shutil
from pathlib import Path

# Répertoire du projet = répertoire parent du dossier contenant ce script
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
VERSIONS_DIR = PROJECT_ROOT / "alembic" / "versions"

FILES_TO_FIX = {
    "9e64f032657f_add_user_date_naissance_telephone_sexe.py": '''"""add_user_date_naissance_telephone_sexe

Revision ID: 9e64f032657f
Revises: add_destinations
Create Date: 2025-12-02 19:15:49.345847

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9e64f032657f'
down_revision = 'add_destinations'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Ajouter les colonnes date_naissance, telephone, sexe à la table users.
    # Utiliser IF NOT EXISTS car date_naissance peut déjà exister (migration e46d145700d0).
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS date_naissance DATE")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS telephone VARCHAR(20)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS sexe VARCHAR(10)")


def downgrade() -> None:
    # Supprimer les colonnes ajoutées (ne pas supprimer date_naissance si gérée par e46d145700d0)
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS sexe")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS telephone")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS date_naissance")
''',
    "a45f38567462_add_resiliation_fields_to_subscriptions.py": '''"""add_resiliation_fields_to_subscriptions

Revision ID: a45f38567462
Revises: 9e64f032657f
Create Date: 2025-12-03 11:49:18.063604

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a45f38567462'
down_revision = '9e64f032657f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Colonnes et index en IF NOT EXISTS pour éviter DuplicateColumn si déjà appliqué (ex. autre branche)
    op.execute("ALTER TABLE souscriptions ADD COLUMN IF NOT EXISTS demande_resiliation VARCHAR(20)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_souscriptions_demande_resiliation ON souscriptions (demande_resiliation)")
    op.execute("ALTER TABLE souscriptions ADD COLUMN IF NOT EXISTS demande_resiliation_date TIMESTAMP")
    op.execute("ALTER TABLE souscriptions ADD COLUMN IF NOT EXISTS demande_resiliation_notes TEXT")
    op.execute("ALTER TABLE souscriptions ADD COLUMN IF NOT EXISTS demande_resiliation_par_agent INTEGER")
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_souscriptions_demande_resiliation_par_agent'
            ) THEN
                ALTER TABLE souscriptions
                ADD CONSTRAINT fk_souscriptions_demande_resiliation_par_agent
                FOREIGN KEY (demande_resiliation_par_agent) REFERENCES users(id) ON DELETE SET NULL;
            END IF;
        END $$
    """)
    op.execute("ALTER TABLE souscriptions ADD COLUMN IF NOT EXISTS demande_resiliation_date_traitement TIMESTAMP")


def downgrade() -> None:
    op.execute("ALTER TABLE souscriptions DROP COLUMN IF EXISTS demande_resiliation_date_traitement")
    op.execute("ALTER TABLE souscriptions DROP CONSTRAINT IF EXISTS fk_souscriptions_demande_resiliation_par_agent")
    op.execute("ALTER TABLE souscriptions DROP COLUMN IF EXISTS demande_resiliation_par_agent")
    op.execute("ALTER TABLE souscriptions DROP COLUMN IF EXISTS demande_resiliation_notes")
    op.execute("ALTER TABLE souscriptions DROP COLUMN IF EXISTS demande_resiliation_date")
    op.execute("DROP INDEX IF EXISTS ix_souscriptions_demande_resiliation")
    op.execute("ALTER TABLE souscriptions DROP COLUMN IF EXISTS demande_resiliation")
''',
    "b2c3d4e5f6a7_add_primes_generees_to_produits.py": '''"""add primes_generees to produits_assurance

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-26

"""
from alembic import op


revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE produits_assurance ADD COLUMN IF NOT EXISTS primes_generees JSON"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE produits_assurance DROP COLUMN IF EXISTS primes_generees")
''',
    "a1b2c3d4e5f6_add_user_nationalite_passeport_contact_urgence.py": '''"""add nationalite, numero_passeport, validite_passeport, contact_urgence to users

Revision ID: a1b2c3d4e5f6
Revises: 0f5d5cb10850
Create Date: 2026-01-26

"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = '0f5d5cb10850'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS nationalite VARCHAR")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS numero_passeport VARCHAR(50)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS validite_passeport DATE")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS contact_urgence VARCHAR(30)")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS contact_urgence")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS validite_passeport")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS numero_passeport")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS nationalite")
''',
    "e5f6a7b8c9d0_add_nom_contact_urgence_to_users.py": '''"""add nom_contact_urgence to users

Revision ID: e5f6a7b8c9d0
Revises: d8e9f0a1b2c3
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa


revision = 'e5f6a7b8c9d0'
down_revision = 'd8e9f0a1b2c3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS nom_contact_urgence VARCHAR(100)")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS nom_contact_urgence")
''',
    "d8e9f0a1b2c3_add_medical_info_to_users.py": '''"""add medical info at registration (maladies_chroniques, traitements, antecedents, grossesse)

Informations médicales recueillies à l'inscription pour validation par le médecin MH.
"""
from alembic import op
import sqlalchemy as sa


revision = 'd8e9f0a1b2c3'
down_revision = 'c7d8e9f0a1b2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS maladies_chroniques TEXT")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS traitements_en_cours TEXT")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS antecedents_recents TEXT")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS grossesse BOOLEAN")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS grossesse")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS antecedents_recents")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS traitements_en_cours")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS maladies_chroniques")
''',
    "c7d8e9f0a1b2_add_inscription_validation_to_users.py": '''"""add inscription validation and email_verified to users

Workflow: inscription (register) -> médecin MH valide -> abonné peut se connecter pour souscrire.
"""
from alembic import op
import sqlalchemy as sa


revision = 'c7d8e9f0a1b2'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS validation_inscription VARCHAR(20)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS validation_inscription_par INTEGER")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS validation_inscription_date TIMESTAMP")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS validation_inscription_notes TEXT")
    # Utilisateurs existants : considérés comme vérifiés et inscription approuvée (rétrocompatibilité)
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        conn.execute(sa.text(
            "UPDATE users SET email_verified = TRUE, validation_inscription = 'approved' WHERE email_verified IS NULL"
        ))
    else:
        conn.execute(sa.text(
            "UPDATE users SET email_verified = 1, validation_inscription = 'approved' WHERE email_verified IS NULL"
        ))
    op.execute("ALTER TABLE users ALTER COLUMN email_verified SET DEFAULT false")
    op.execute("ALTER TABLE users ALTER COLUMN email_verified SET NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_validation_inscription ON users (validation_inscription)")
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_users_validation_inscription_par_users'
            ) THEN
                ALTER TABLE users ADD CONSTRAINT fk_users_validation_inscription_par_users
                FOREIGN KEY (validation_inscription_par) REFERENCES users(id) ON DELETE SET NULL;
            END IF;
        END $$
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS fk_users_validation_inscription_par_users")
    op.execute("DROP INDEX IF EXISTS ix_users_validation_inscription")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS validation_inscription_notes")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS validation_inscription_date")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS validation_inscription_par")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS validation_inscription")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS email_verified")
''',
    "a9b8c7d6e5f4_add_destination_country_id_to_projets_voyage.py": '''"""Add destination_country_id to projets_voyage

Revision ID: a9b8c7d6e5f4
Revises: b8c9d0e1f2a3
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa


revision = 'a9b8c7d6e5f4'
down_revision = 'b8c9d0e1f2a3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE projets_voyage ADD COLUMN IF NOT EXISTS destination_country_id INTEGER")
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_projets_voyage_destination_country_id'
            ) THEN
                ALTER TABLE projets_voyage ADD CONSTRAINT fk_projets_voyage_destination_country_id
                FOREIGN KEY (destination_country_id) REFERENCES destination_countries(id) ON DELETE SET NULL;
            END IF;
        END $$
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_projets_voyage_destination_country_id ON projets_voyage (destination_country_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_projets_voyage_destination_country_id")
    op.execute("ALTER TABLE projets_voyage DROP CONSTRAINT IF EXISTS fk_projets_voyage_destination_country_id")
    op.execute("ALTER TABLE projets_voyage DROP COLUMN IF EXISTS destination_country_id")
''',
}


def main():
    if not VERSIONS_DIR.is_dir():
        print(f"ERREUR: Répertoire des migrations introuvable: {VERSIONS_DIR}")
        print("Exécutez ce script depuis la racine du projet.")
        return 1

    backup_dir = VERSIONS_DIR.parent / "versions_backup_before_idempotent_fix"
    if not backup_dir.exists():
        shutil.copytree(VERSIONS_DIR, backup_dir)
        print(f"Sauvegarde créée: {backup_dir}")

    for filename, content in FILES_TO_FIX.items():
        path = VERSIONS_DIR / filename
        if path.exists():
            path.write_text(content, encoding="utf-8")
            print(f"  Corrigé: {filename}")
        else:
            print(f"  Ignoré (absent): {filename}")

    print("\nMigrations idempotentes appliquées.")
    print("Lancez ensuite: sudo docker compose exec api alembic upgrade head")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
