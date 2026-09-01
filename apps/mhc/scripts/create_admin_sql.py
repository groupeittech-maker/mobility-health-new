#!/usr/bin/env python3
"""
Créer l'utilisateur admin en SQL brut (rôle en minuscules pour PostgreSQL).
À utiliser quand create_test_users.py échoue à cause de l'enum (ADMIN vs admin).
Usage: python scripts/create_admin_sql.py
"""
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bcrypt
from sqlalchemy import text
from app.core.database import engine

def create_admin():
    password = "admin123"
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    now = datetime.now(timezone.utc)

    with engine.connect() as conn:
        # Vérifier si admin existe déjà
        row = conn.execute(
            text("SELECT id FROM users WHERE username = 'admin'")
        ).fetchone()
        if row:
            print("L'utilisateur admin existe déjà. Mise à jour du mot de passe...")
            conn.execute(
                text("UPDATE users SET hashed_password = :hash, updated_at = :now WHERE username = 'admin'"),
                {"hash": hashed, "now": now}
            )
            conn.commit()
            print("✓ Mot de passe admin mis à jour: admin123")
            return

        # Insert avec rôle en minuscules (valeur enum PostgreSQL)
        conn.execute(
            text("""
                INSERT INTO users (
                    email, username, hashed_password, full_name,
                    is_active, is_superuser, role, created_at, updated_at
                ) VALUES (
                    :email, :username, :hash, :full_name,
                    true, true, 'admin', :created_at, :updated_at
                )
            """),
            {
                "email": "admin@mobilityhealth.com",
                "username": "admin",
                "hash": hashed,
                "full_name": "Administrateur Principal",
                "created_at": now,
                "updated_at": now,
            },
        )
        conn.commit()
        print("✓ Utilisateur admin créé.")
        print("  Identifiant: admin")
        print("  Mot de passe: admin123")


if __name__ == "__main__":
    create_admin()
