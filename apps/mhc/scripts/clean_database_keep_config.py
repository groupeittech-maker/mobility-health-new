"""
Script de nettoyage de la base de données Mobility Health.

Conserve les configurations de base :
- roles
- assureurs
- produits_assurance
- hospitals, hospital_act_tarifs, hospital_exam_tarifs
- destination_countries, destination_cities
- utilisateur(s) admin (role = 'admin')

Supprime toutes les autres données (souscriptions, projets, attestations,
factures, sinistres, utilisateurs non-admin, etc.) pour tester le logiciel à neuf.

Usage :
  python scripts/clean_database_keep_config.py
  python scripts/clean_database_keep_config.py --dry-run   # Affiche les actions sans exécuter
  python scripts/clean_database_keep_config.py --yes       # Pas de confirmation

À exécuter depuis la racine du projet. Vérifier qu’au moins un utilisateur admin existe avant.
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import SessionLocal, engine
from app.core.enums import Role


# Ordre de suppression (enfants avant parents, respect des FK)
DELETE_ORDER = [
    "invoice_history",
    "invoice_items",
    "invoices",
    "validations_attestation",
    "attestations",
    "sinistre_process_steps",
    "sinistres",
    "hospital_stays",
    "prestations",
    "rapports",
    "questionnaires",
    "notifications",
    "finance_refunds",
    "finance_repartitions",
    "finance_movements",
    "finance_accounts",
    "paiements",
    "ia_analysis_documents",
    "ia_analysis_assureurs",
    "ia_analyses",
    "historique_prix",
    "projet_voyage_documents",
    "souscriptions",
    "projets_voyage",
    "contacts_proches",
    "audit_logs",
    "transaction_logs",
    "alertes",
    "failed_tasks",
    "assureur_agents",
]


def run_clean(db, dry_run: bool):
    """Exécute les suppressions et la conservation des configs."""
    dialect = engine.dialect.name
    if dialect == "sqlite":
        db.execute(text("PRAGMA foreign_keys = ON"))

    for table in DELETE_ORDER:
        if dry_run:
            try:
                r = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = r.scalar() or 0
                print(f"  [DRY-RUN] DELETE FROM {table} (~{count} lignes)")
            except Exception as e:
                print(f"  [DRY-RUN] {table}: table peut ne pas exister - {e}")
        else:
            try:
                db.execute(text(f"DELETE FROM {table}"))
                print(f"  Supprimé : {table}")
            except Exception as e:
                err = str(e).lower()
                if "no such table" in err or "does not exist" in err or "relation" in err:
                    print(f"  Ignoré (table absente) : {table}")
                else:
                    print(f"  Erreur sur {table}: {e}")
                    raise

    # Mettre à NULL les FK vers users non-admin (avant de supprimer les users)
    if dry_run:
        print("  [DRY-RUN] Mise à NULL de hospitals.medecin_referent_id et assureurs.agent_comptable_id pour non-admin")
    else:
        db.execute(
            text("""
                UPDATE hospitals SET medecin_referent_id = NULL
                WHERE medecin_referent_id IS NOT NULL
                AND medecin_referent_id IN (SELECT id FROM users WHERE role != :admin_role)
            """),
            {"admin_role": Role.ADMIN.value},
        )
        db.execute(
            text("""
                UPDATE assureurs SET agent_comptable_id = NULL
                WHERE agent_comptable_id IS NOT NULL
                AND agent_comptable_id IN (SELECT id FROM users WHERE role != :admin_role)
            """),
            {"admin_role": Role.ADMIN.value},
        )
        print("  Mise à NULL des FK vers users non-admin (hospitals, assureurs)")

    # Supprimer les utilisateurs non-admin
    if dry_run:
        r = db.execute(
            text("SELECT COUNT(*) FROM users WHERE role != :admin_role"),
            {"admin_role": Role.ADMIN.value},
        )
        count = r.scalar() or 0
        print(f"  [DRY-RUN] DELETE users non-admin (~{count} lignes)")
    else:
        r = db.execute(
            text("DELETE FROM users WHERE role != :admin_role"),
            {"admin_role": Role.ADMIN.value},
        )
        print("  Supprimé : users (non-admin)")


def main():
    parser = argparse.ArgumentParser(description="Nettoyer la BDD en conservant les configs de base.")
    parser.add_argument("--dry-run", action="store_true", help="Afficher les actions sans exécuter")
    parser.add_argument("--yes", "-y", action="store_true", help="Ne pas demander de confirmation")
    args = parser.parse_args()

    print("Nettoyage base Mobility Health")
    print("Conservé : roles, assureurs, produits_assurance, hospitals, hospital_act_tarifs,")
    print("           hospital_exam_tarifs, destination_countries, destination_cities, utilisateur(s) admin.")
    print("Tout le reste sera supprimé.")
    if args.dry_run:
        print("Mode DRY-RUN : aucune modification.")
    if not args.yes and not args.dry_run:
        rep = input("Continuer ? (oui/non) ")
        if rep.strip().lower() not in ("oui", "o", "yes", "y"):
            print("Annulé.")
            sys.exit(0)

    db = SessionLocal()
    try:
        run_clean(db, dry_run=args.dry_run)
        if not args.dry_run:
            db.commit()
            print("Commit effectué.")
    except Exception as e:
        db.rollback()
        print("Erreur, rollback:", e)
        sys.exit(1)
    finally:
        db.close()

    print("Terminé.")


if __name__ == "__main__":
    main()
