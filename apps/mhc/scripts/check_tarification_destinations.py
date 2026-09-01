"""
Contrôle de cohérence : zones tarifaires canoniques (grille voyage) ↔ destination_countries.

À lancer après init des pays (scripts/init_destinations.py) et configuration admin des zones.

Usage:
  python scripts/check_tarification_destinations.py
  python scripts/check_tarification_destinations.py --strict   # code retour 1 si zone manquante

Vérifie :
  - existence d’une ligne tarification_zones active par code canonique (INTRA_AFRIQUE, …) ;
  - pays rattachés (tarification_zone_pays) pour chaque zone canonique ;
  - pays actifs du référentiel non rattachés à aucune zone (avertissement).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.destination import DestinationCountry
from app.models.tarification import TarificationZone, TarificationZonePays
from app.services.voyage_premium_calculator import ZONES_CANONIQUES, normalize_zone_code


def _norm_zone_code(raw: str | None) -> str | None:
    if not raw or not str(raw).strip():
        return None
    try:
        return normalize_zone_code(raw)
    except Exception:
        return None


def run_check(db: Session, strict: bool) -> int:
    exit_code = 0
    all_zones = db.query(TarificationZone).all()
    by_canon: dict[str, list[TarificationZone]] = {c: [] for c in ZONES_CANONIQUES}
    for z in all_zones:
        nc = _norm_zone_code(z.code)
        if nc and nc in by_canon and z.est_actif:
            by_canon[nc].append(z)

    print("=== Zones canoniques (grille voyage JSON) ===\n")
    for code in sorted(ZONES_CANONIQUES):
        matches = by_canon[code]
        if not matches:
            print(f"  [ERREUR] Aucune zone active avec le code « {code} ».")
            exit_code = 1
            continue
        if len(matches) > 1:
            print(f"  [ATTENTION] Plusieurs zones actives pour « {code} » (ids: {[m.id for m in matches]}).")
        z = matches[0]
        n_pays = (
            db.query(TarificationZonePays)
            .filter(TarificationZonePays.zone_id == z.id)
            .count()
        )
        if n_pays == 0:
            print(f"  [ATTENTION] Zone « {code} » (id={z.id}) : aucun pays rattaché.")
        else:
            print(f"  [OK] {code} → zone id={z.id}, {n_pays} pays rattaché(s).")

    linked_ids = {
        row.destination_country_id
        for row in db.query(TarificationZonePays).all()
    }
    active_countries = (
        db.query(DestinationCountry)
        .filter(DestinationCountry.est_actif == True)  # noqa: E712
        .all()
    )
    orphan = [c for c in active_countries if c.id not in linked_ids]

    print("\n=== Pays actifs sans zone tarifaire ===\n")
    if not orphan:
        print("  Aucun : tous les pays actifs sont rattachés à au moins une zone.")
    else:
        print(f"  {len(orphan)} pays actifs non rattachés (devis par grille JSON impossible pour eux) :")
        for c in sorted(orphan, key=lambda x: x.nom)[:40]:
            print(f"    - id={c.id}  {c.nom!r}  (code {c.code!r})")
        if len(orphan) > 40:
            print(f"    … et {len(orphan) - 40} autre(s).")

    print(
        "\nRappel : les formulaires utilisent le champ « nom » de destination_countries ; "
        "l’API devis résout le pays par id ou par ce libellé (normalisé)."
    )

    return exit_code if strict else 0


def main() -> None:
    strict = "--strict" in sys.argv
    db: Session = SessionLocal()
    try:
        code = run_check(db, strict=strict)
        sys.exit(code)
    finally:
        db.close()


if __name__ == "__main__":
    main()
