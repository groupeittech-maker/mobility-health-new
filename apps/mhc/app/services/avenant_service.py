"""Actions sur une police (workflow MyMHC V3) : annulation, modification, prorogation.

Règles :
- une seule demande en cours par attestation : tant qu'une modification ou
  une prorogation attend son paiement, les deux autres actions sont bloquées ;
- annulation (avenant 102) : avant la date d'effet, même pendant une
  validation en attente ; confirmation explicite ; si la police est payée,
  une ristourne est enregistrée « à rembourser » (suivie séparément) ;
- modification (avenant 107) : avant l'expiration, y compris pendant le séjour ;
  changement de destination dans la même zone tarifaire, durée restante et date
  d'expiration inchangées, sans supplément ni remboursement ; appliquée après
  confirmation de l'assuré, avenant généré immédiatement ;
- prorogation (avenant 108) : jusqu'à la date de fin initiale, durée totale
  ≤ 92 jours ; prime complémentaire au prorata, encaissée dans l'application.
  Échec de paiement = ni confirmation ni document.
La suspension et la réémission n'existent pas dans MyMHC.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import MAX_TRIP_DAYS
from app.core.enums import StatutPaiement, StatutSouscription
from app.models.attestation import Attestation
from app.models.avenant import Avenant
from app.models.paiement import Paiement
from app.models.projet_voyage import ProjetVoyage
from app.models.ristourne import Ristourne
from app.models.souscription import Souscription
from app.models.user import User
from app.services.attestation_service import AttestationService

logger = logging.getLogger(__name__)

TYPE_ANNULATION = "annulation"
TYPE_MODIFICATION = "modification"
TYPE_PROROGATION = "prorogation"
ACTION_TYPES = (TYPE_ANNULATION, TYPE_MODIFICATION, TYPE_PROROGATION)

STATUT_ATTENTE_PAIEMENT = "attente_paiement"
STATUT_EMIS = "emis"
STATUT_ABANDONNE = "abandonne"
STATUTS_EN_COURS = (STATUT_ATTENTE_PAIEMENT,)

NATURE_COMPLEMENT = "complement"
NATURE_REMBOURSEMENT = "remboursement"
NATURE_AUCUN = "aucun"

RISTOURNE_A_REMBOURSER = "a_rembourser"
RISTOURNE_REMBOURSE = "rembourse"
RISTOURNE_MOYENS = ("carte", "mobile_money", "virement", "autre")

_TERMINAL_STATUSES = {
    StatutSouscription.RESILIEE,
    StatutSouscription.REFUSEE,
    StatutSouscription.EXPIREE,
}
_ONE = Decimal("1")


class AvenantError(ValueError):
    """Erreur métier des actions sur une police (→ HTTP 400)."""


@dataclass
class Montants:
    """Ventilation d'un montant de prime (complément ou remboursement)."""

    prime: Decimal = Decimal("0")
    frais_police: Decimal = Decimal("0")
    frais_services: Decimal = Decimal("0")
    taxes: Decimal = Decimal("0")

    @property
    def total(self) -> Decimal:
        return self.prime + self.frais_police + self.frais_services + self.taxes

    def negate(self) -> "Montants":
        return Montants(-self.prime, -self.frais_police, -self.frais_services, -self.taxes)

    def as_payload(self) -> dict[str, str]:
        return {
            "prime": str(self.prime),
            "frais_police": str(self.frais_police),
            "frais_services": str(self.frais_services),
            "taxes": str(self.taxes),
            "total": str(self.total),
        }

    @classmethod
    def from_payload(cls, data: Optional[dict]) -> "Montants":
        data = data or {}
        return cls(*(_dec(data.get(k)) for k in ("prime", "frais_police", "frais_services", "taxes")))


@dataclass
class ActionResult:
    souscription: Souscription
    avenant: Optional[Avenant] = None
    ristourne: Optional[Ristourne] = None
    montants: Optional[Montants] = None
    nature: Optional[str] = None
    simulation: bool = False
    paiement: Optional[Paiement] = None
    payment_info: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _dec(value: Any) -> Decimal:
    try:
        return Decimal(str(value if value is not None else 0))
    except Exception:
        return Decimal("0")


def _round(value: Decimal) -> Decimal:
    return value.quantize(_ONE, rounding=ROUND_HALF_UP)


def _as_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value)[:10]).date()


def _as_datetime(value: date) -> datetime:
    return datetime.combine(value, time.min)


def _today(today: Optional[date]) -> date:
    return today or datetime.utcnow().date()


def _statut(souscription: Souscription) -> StatutSouscription:
    statut = souscription.statut
    return statut if isinstance(statut, StatutSouscription) else StatutSouscription(str(statut))


def _max_days(souscription: Souscription) -> int:
    produit = getattr(souscription, "produit_assurance", None)
    product_max = getattr(produit, "duree_max_jours", None)
    return min(MAX_TRIP_DAYS, product_max) if product_max else MAX_TRIP_DAYS


def _coverage_days(souscription: Souscription) -> int:
    if not souscription.date_debut or not souscription.date_fin:
        raise AvenantError("Les dates de couverture de la police sont incomplètes.")
    return max(1, (_as_date(souscription.date_fin) - _as_date(souscription.date_debut)).days)


def _components(souscription: Souscription) -> Montants:
    """Ventilation de la prime courante (prix = prime + coût police + frais + taxes)."""
    total = _dec(souscription.prix_applique)
    frais_police = _dec(souscription.cout_police)
    frais_services = _dec(souscription.frais_services)
    taxes = _dec(souscription.taxes_total)
    if souscription.prime_assurance is not None:
        prime = _dec(souscription.prime_assurance)
    else:
        prime = max(total - frais_police - frais_services - taxes, Decimal("0"))
    return Montants(prime, frais_police, frais_services, taxes)


def _prorata(souscription: Souscription, numerator: int, denominator: int) -> Montants:
    """Part variable (hors coût de police forfaitaire) au prorata d'une durée."""
    base = _components(souscription)
    ratio = Decimal(numerator) / Decimal(denominator)
    return Montants(
        prime=_round(base.prime * ratio),
        frais_services=_round(base.frais_services * ratio),
        taxes=_round(base.taxes * ratio),
    )


def _is_paid(db: Session, souscription: Souscription) -> bool:
    return _original_payment(db, souscription) is not None


def _original_payment(db: Session, souscription: Souscription) -> Optional[Paiement]:
    """Paiement de la souscription (hors compléments d'avenant)."""
    complement_ids = [
        row[0]
        for row in db.query(Avenant.paiement_id)
        .filter(Avenant.souscription_id == souscription.id, Avenant.paiement_id.isnot(None))
        .all()
    ]
    query = db.query(Paiement).filter(
        Paiement.souscription_id == souscription.id,
        Paiement.statut == StatutPaiement.VALIDE,
    )
    if complement_ids:
        query = query.filter(Paiement.id.notin_(complement_ids))
    return query.order_by(Paiement.created_at.asc()).first()


def _provisional_number() -> str:
    return f"PROV-{uuid.uuid4().hex[:12].upper()}"


def _allocate_number(db: Session, type_avenant: str) -> str:
    from app.services.mhc_reference_service import (
        allocate_avenant_annulation_number,
        allocate_avenant_modification_number,
        allocate_avenant_prorogation_number,
    )

    return {
        TYPE_ANNULATION: allocate_avenant_annulation_number,
        TYPE_MODIFICATION: allocate_avenant_modification_number,
        TYPE_PROROGATION: allocate_avenant_prorogation_number,
    }[type_avenant](db)


def _notify(souscription: Souscription, titre: str, message: str) -> None:
    try:
        from app.services.notification_service import NotificationService

        NotificationService.create_notification(
            user_id=souscription.user_id,
            type_notification="police_action",
            titre=titre,
            message=message,
            lien_relation_id=souscription.id,
            lien_relation_type="souscription",
            channels=["push"],
        )
    except Exception as exc:  # pragma: no cover - notification best effort
        logger.warning("Notification impossible pour la souscription %s : %s", souscription.id, exc)


def _traveler_and_minors(db: Session, souscription: Souscription):
    traveler_info = AttestationService._extract_traveler_info(db, souscription.id)
    minors_info = AttestationService._extract_minors_from_notes(souscription.notes or "")
    if not minors_info and souscription.projet_voyage_id:
        projet = db.query(ProjetVoyage).filter(ProjetVoyage.id == souscription.projet_voyage_id).first()
        if projet and getattr(projet, "notes", None):
            minors_info = AttestationService._extract_minors_from_notes(projet.notes)
    return traveler_info, minors_info


# ---------------------------------------------------------------------------
# Disponibilité des actions (règle exclusive)
# ---------------------------------------------------------------------------
def pending_action(db: Session, souscription: Souscription) -> Optional[Avenant]:
    return (
        db.query(Avenant)
        .filter(
            Avenant.souscription_id == souscription.id,
            Avenant.type_avenant.in_(ACTION_TYPES),
            Avenant.statut.in_(STATUTS_EN_COURS),
        )
        .order_by(Avenant.created_at.desc())
        .first()
    )


_ACTION_LABELS = {
    TYPE_ANNULATION: "annulation",
    TYPE_MODIFICATION: "modification",
    TYPE_PROROGATION: "prorogation",
}


def _blocker(db: Session, souscription: Souscription, action: str, today: date) -> Optional[str]:
    """Motif empêchant l'action, ou None si elle est permise."""
    statut = _statut(souscription)
    if statut == StatutSouscription.EXPIREE:
        return "Police expirée : une nouvelle souscription est requise."
    if statut in _TERMINAL_STATUSES:
        return "Cette police n'est plus modifiable."
    pending = pending_action(db, souscription)
    if pending is not None:
        return (
            f"Une demande de {_ACTION_LABELS.get(pending.type_avenant, pending.type_avenant)} est déjà en cours "
            "sur cette attestation."
        )
    debut = _as_date(souscription.date_debut)
    fin = _as_date(souscription.date_fin)
    if action == TYPE_ANNULATION:
        if debut is None or today >= debut:
            return "L'annulation n'est possible qu'avant la date d'effet de la police."
        if statut in {StatutSouscription.EN_ATTENTE, StatutSouscription.PENDING}:
            return "Un brouillon se supprime directement depuis la liste « En attente »."
        in_flight = (
            db.query(Paiement.id)
            .filter(Paiement.souscription_id == souscription.id, Paiement.statut == StatutPaiement.EN_COURS)
            .first()
        )
        if in_flight:
            return "Un paiement est en cours de traitement : réessayez une fois celui-ci finalisé."
        return None
    if statut != StatutSouscription.ACTIVE:
        return "Action disponible uniquement sur une police payée et validée."
    if action == TYPE_MODIFICATION:
        if fin is None or today > fin:
            return "La modification n'est possible qu'avant l'expiration de la police."
        return None
    if action == TYPE_PROROGATION:
        if fin is None or today > fin:
            return "La prorogation n'est plus possible après la date de fin de couverture initiale."
        if (fin - debut).days >= _max_days(souscription):
            return f"La durée maximale de couverture ({_max_days(souscription)} jours) est déjà atteinte."
        return None
    return "Action inconnue."


def available_actions(db: Session, souscription: Souscription, today: Optional[date] = None) -> dict[str, Any]:
    day = _today(today)
    actions = {}
    for action in ACTION_TYPES:
        motif = _blocker(db, souscription, action, day)
        actions[action] = {"disponible": motif is None, "motif": motif}
    return {
        "actions": actions,
        "action_en_cours": pending_action(db, souscription),
        "duree_max_jours": _max_days(souscription),
    }


def _ensure_allowed(db: Session, souscription: Souscription, action: str, today: date) -> None:
    motif = _blocker(db, souscription, action, today)
    if motif:
        raise AvenantError(motif)


# ---------------------------------------------------------------------------
# Annulation (102)
# ---------------------------------------------------------------------------
def annulation_refund(souscription: Souscription) -> Montants:
    base = _components(souscription)
    return Montants(
        prime=base.prime,
        frais_police=base.frais_police if settings.ANNULATION_REMBOURSE_COUT_POLICE else Decimal("0"),
        frais_services=base.frais_services if settings.ANNULATION_REMBOURSE_FRAIS_SERVICES else Decimal("0"),
        taxes=base.taxes,
    )


def request_annulation(
    db: Session,
    souscription: Souscription,
    actor: Optional[User],
    *,
    confirm: bool,
    motif: Optional[str] = None,
    today: Optional[date] = None,
) -> ActionResult:
    day = _today(today)
    _ensure_allowed(db, souscription, TYPE_ANNULATION, day)
    paiement = _original_payment(db, souscription)
    montants = annulation_refund(souscription) if paiement else Montants()
    if not confirm:
        return ActionResult(souscription, montants=montants, simulation=True,
                            nature=NATURE_REMBOURSEMENT if montants.total > 0 else NATURE_AUCUN)

    now = datetime.utcnow()
    souscription.statut = StatutSouscription.RESILIEE
    avenant = ristourne = None
    if paiement is not None:
        for attestation in db.query(Attestation).filter(Attestation.souscription_id == souscription.id).all():
            attestation.est_valide = False
        avenant = Avenant(
            souscription_id=souscription.id,
            type_avenant=TYPE_ANNULATION,
            numero=_allocate_number(db, TYPE_ANNULATION),
            statut=STATUT_EMIS,
            motif_autre=(motif or "").strip() or None,
            date_effet=now,
            date_debut_initiale=souscription.date_debut,
            date_fin_initiale=souscription.date_fin,
            montant_ajustement=montants.total,
            nature_ajustement=NATURE_REMBOURSEMENT if montants.total > 0 else NATURE_AUCUN,
            payload={"montants": montants.as_payload()},
            created_by_id=getattr(actor, "id", None),
        )
        db.add(avenant)
        db.flush()
        if montants.total > 0:
            ristourne = _create_ristourne(
                db, souscription, avenant, paiement, montants,
                motif=f"Annulation de la police avant sa date d'effet (avenant {avenant.numero})",
            )
    db.flush()
    _notify(
        souscription,
        "Police annulée",
        f"Votre police {souscription.numero_souscription} est annulée."
        + (" Le remboursement applicable est en cours de traitement." if ristourne else ""),
    )
    return ActionResult(souscription, avenant=avenant, ristourne=ristourne, montants=montants,
                        nature=avenant.nature_ajustement if avenant else NATURE_AUCUN)


# ---------------------------------------------------------------------------
# Modification (107)
# ---------------------------------------------------------------------------
def _validate_period(souscription: Souscription, debut: date, fin: date) -> int:
    if fin <= debut:
        raise AvenantError("La date de fin doit être postérieure à la date de début.")
    days = (fin - debut).days
    max_days = _max_days(souscription)
    if days > max_days:
        raise AvenantError(f"La durée totale de couverture ne peut pas dépasser {max_days} jours ({days} demandés).")
    return days


def _tariff_zone(db: Session, souscription: Souscription, destination_country_id: Optional[int]) -> Optional[str]:
    """Zone tarifaire du parcours pays de résidence → destination."""
    if not destination_country_id:
        return None
    from app.services.prime_tarif_service import resolve_residence_country_id_for_pricing
    from app.services.voyage_premium_calculator import resolve_voyage_tariff_zone_code

    user = souscription.user or db.query(User).filter(User.id == souscription.user_id).first()
    residence_id = resolve_residence_country_id_for_pricing(
        db, None, souscription.projet_voyage, getattr(user, "pays_residence", None)
    )
    return resolve_voyage_tariff_zone_code(db, residence_id, destination_country_id, None)


def _destination_display(projet: Optional[ProjetVoyage], country, ville: Optional[str] = None) -> str:
    nom = getattr(country, "nom", None) or (getattr(projet, "destination", None) if projet else None) or "—"
    return f"{ville.strip()}, {nom}" if ville and ville.strip() else str(nom)


def request_modification(
    db: Session,
    souscription: Souscription,
    actor: Optional[User],
    *,
    destination_country_id: Optional[int],
    destination_ville: Optional[str] = None,
    confirm: bool,
    motif: Optional[str] = None,
    today: Optional[date] = None,
) -> ActionResult:
    """Modification (107) : nouvelle destination dans la même zone tarifaire.

    La période de couverture (durée restante, date d'expiration) est inchangée et
    aucun ajustement de prime n'est appliqué. Sur confirmation, l'avenant est émis.
    """
    from app.models.destination import DestinationCountry

    day = _today(today)
    _ensure_allowed(db, souscription, TYPE_MODIFICATION, day)
    if not destination_country_id:
        raise AvenantError("La nouvelle destination est obligatoire.")
    pays = db.query(DestinationCountry).filter(DestinationCountry.id == destination_country_id).first()
    if pays is None:
        raise AvenantError("Destination inconnue.")
    projet = souscription.projet_voyage
    ancien_pays_id = getattr(projet, "destination_country_id", None) if projet else None
    ancienne = _destination_display(projet, getattr(projet, "destination_country", None) if projet else None)
    ville = (destination_ville or "").strip() or None
    if ancien_pays_id == pays.id and (not ville or (projet and (projet.destination or "").strip().lower() == ville.lower())):
        raise AvenantError("La nouvelle destination est identique à la destination actuelle.")

    zone_initiale = _tariff_zone(db, souscription, ancien_pays_id)
    zone_nouvelle = _tariff_zone(db, souscription, pays.id)
    if not zone_initiale or not zone_nouvelle or zone_initiale != zone_nouvelle:
        raise AvenantError(
            "La nouvelle destination doit appartenir à la même zone tarifaire que la destination initiale "
            f"({zone_initiale or 'zone inconnue'}). Pour une autre zone, une nouvelle souscription est requise."
        )
    nouvelle = _destination_display(projet, pays, ville)
    montants = Montants()
    if not confirm:
        return ActionResult(souscription, montants=montants, nature=NATURE_AUCUN, simulation=True,
                            payment_info={"ancienne_destination": ancienne, "nouvelle_destination": nouvelle,
                                          "zone_tarifaire": zone_nouvelle})

    now = datetime.utcnow()
    avenant = Avenant(
        souscription_id=souscription.id,
        type_avenant=TYPE_MODIFICATION,
        numero=_allocate_number(db, TYPE_MODIFICATION),
        statut=STATUT_EMIS,
        motif_autre=(motif or "").strip() or None,
        date_effet=now,
        date_echeance=souscription.date_fin,
        date_debut_initiale=souscription.date_debut,
        date_fin_initiale=souscription.date_fin,
        nouvelle_date_debut=souscription.date_debut,
        nouvelle_date_fin=souscription.date_fin,
        montant_ajustement=Decimal("0"),
        nature_ajustement=NATURE_AUCUN,
        payload={
            "ancienne_destination": ancienne,
            "ancien_destination_country_id": ancien_pays_id,
            "nouvelle_destination": nouvelle,
            "destination_country_id": pays.id,
            "zone_tarifaire": zone_nouvelle,
        },
        created_by_id=getattr(actor, "id", None),
    )
    db.add(avenant)
    if projet is not None:
        projet.destination_country_id = pays.id
        projet.destination = ville or pays.nom
    db.flush()
    _regenerate_attestation(db, souscription, None)
    _notify(
        souscription,
        "Avenant de modification émis",
        f"La destination de votre police {souscription.numero_souscription} est désormais : {nouvelle}. "
        "Les dates de couverture sont inchangées.",
    )
    return ActionResult(souscription, avenant=avenant, montants=montants, nature=NATURE_AUCUN,
                        payment_info={"ancienne_destination": ancienne, "nouvelle_destination": nouvelle,
                                      "zone_tarifaire": zone_nouvelle})


# ---------------------------------------------------------------------------
# Prorogation (108)
# ---------------------------------------------------------------------------
def request_prorogation(
    db: Session,
    souscription: Souscription,
    actor: Optional[User],
    *,
    nouvelle_date_fin: Any,
    confirm: bool,
    motif: Optional[str] = None,
    today: Optional[date] = None,
) -> ActionResult:
    day = _today(today)
    _ensure_allowed(db, souscription, TYPE_PROROGATION, day)
    fin = _as_date(nouvelle_date_fin)
    fin_initiale = _as_date(souscription.date_fin)
    if fin is None:
        raise AvenantError("La nouvelle date de fin de couverture est obligatoire.")
    if fin <= fin_initiale:
        raise AvenantError("La nouvelle date de fin doit être postérieure à la date de fin actuelle.")
    _validate_period(souscription, _as_date(souscription.date_debut), fin)

    montants = _prorata(souscription, (fin - fin_initiale).days, _coverage_days(souscription))
    if not confirm:
        return ActionResult(souscription, montants=montants, nature=NATURE_COMPLEMENT, simulation=True)

    avenant = Avenant(
        souscription_id=souscription.id,
        type_avenant=TYPE_PROROGATION,
        numero=_provisional_number(),
        statut=STATUT_ATTENTE_PAIEMENT,
        motif_autre=(motif or "").strip() or None,
        date_effet=souscription.date_fin,
        date_debut_initiale=souscription.date_debut,
        date_fin_initiale=souscription.date_fin,
        nouvelle_date_debut=souscription.date_debut,
        nouvelle_date_fin=_as_datetime(fin),
        montant_ajustement=montants.total,
        nature_ajustement=NATURE_COMPLEMENT,
        payload={"delta": montants.as_payload()},
        created_by_id=getattr(actor, "id", None),
    )
    db.add(avenant)
    db.flush()
    return ActionResult(souscription, avenant=avenant, montants=montants, nature=NATURE_COMPLEMENT)


# ---------------------------------------------------------------------------
# Application, paiement du complément, abandon
# ---------------------------------------------------------------------------
def _regenerate_attestation(db: Session, souscription: Souscription, paiement: Optional[Paiement]) -> None:
    """Nouvelle version de l'attestation aux dates à jour ; les anciennes restent en interne."""
    paiement = paiement or _original_payment(db, souscription)
    user = db.query(User).filter(User.id == souscription.user_id).first()
    if paiement is None or user is None:
        return
    previous = (
        db.query(Attestation)
        .filter(Attestation.souscription_id == souscription.id, Attestation.est_valide == True)  # noqa: E712
        .all()
    )
    try:
        new = AttestationService.create_attestation_definitive(db=db, souscription=souscription, paiement=paiement, user=user)
    except Exception as exc:
        logger.warning("Attestation non régénérée pour la souscription %s : %s", souscription.id, exc)
        return
    for attestation in previous:
        if attestation.id != getattr(new, "id", None):
            attestation.est_valide = False


def _apply_avenant(db: Session, avenant: Avenant, paiement: Optional[Paiement] = None) -> None:
    """Applique les nouvelles dates et la prime ajustée, puis émet l'avenant."""
    souscription = avenant.souscription or db.query(Souscription).get(avenant.souscription_id)
    # Delta signé : négatif pour une modification à la baisse (remboursement).
    delta = Montants.from_payload((avenant.payload or {}).get("delta"))

    souscription.date_debut = avenant.nouvelle_date_debut or souscription.date_debut
    souscription.date_fin = avenant.nouvelle_date_fin or souscription.date_fin
    souscription.prix_applique = _dec(souscription.prix_applique) + delta.total
    if souscription.prime_assurance is not None:
        souscription.prime_assurance = _dec(souscription.prime_assurance) + delta.prime
    if souscription.frais_services is not None:
        souscription.frais_services = _dec(souscription.frais_services) + delta.frais_services
    if souscription.taxes_total is not None:
        souscription.taxes_total = _dec(souscription.taxes_total) + delta.taxes
    projet = souscription.projet_voyage
    if projet is not None:
        projet.date_depart = souscription.date_debut
        projet.date_retour = souscription.date_fin

    avenant.numero = _allocate_number(db, avenant.type_avenant)
    avenant.statut = STATUT_EMIS
    avenant.date_effet = avenant.date_effet or datetime.utcnow()
    avenant.date_echeance = souscription.date_fin
    db.flush()
    _regenerate_attestation(db, souscription, paiement)
    label = "modification" if avenant.type_avenant == TYPE_MODIFICATION else "prorogation"
    _notify(
        souscription,
        f"Avenant de {label} émis",
        f"Votre police {souscription.numero_souscription} est désormais valable du "
        f"{souscription.date_debut:%d/%m/%Y} au {souscription.date_fin:%d/%m/%Y}.",
    )


def avenant_for_payment(db: Session, paiement_id: int) -> Optional[Avenant]:
    return db.query(Avenant).filter(Avenant.paiement_id == paiement_id).first()


def finalize_avenant_payment(db: Session, avenant: Avenant, paiement: Paiement) -> Avenant:
    """Paiement du complément confirmé : applique l'avenant et émet la quittance 119."""
    paiement.statut = StatutPaiement.VALIDE
    paiement.date_paiement = paiement.date_paiement or datetime.utcnow()
    if avenant.statut != STATUT_ATTENTE_PAIEMENT:
        return avenant
    _apply_avenant(db, avenant, None)
    souscription = avenant.souscription or db.query(Souscription).get(avenant.souscription_id)
    delta = Montants.from_payload((avenant.payload or {}).get("delta"))
    try:
        user = db.query(User).filter(User.id == paiement.user_id).first()
        AttestationService.issue_quittance_paiement(
            db, souscription, paiement, user,
            breakdown={"prime": delta.prime, "cout_police": delta.frais_police, "taxes": delta.frais_services + delta.taxes},
        )
    except Exception as exc:
        logger.warning("Quittance non générée pour le complément %s : %s", paiement.id, exc)
    db.flush()
    return avenant


def start_avenant_payment(
    db: Session,
    avenant: Avenant,
    payer: User,
    *,
    payment_type: str,
    flow: str = "checkout",
) -> ActionResult:
    """Encaisse le complément de prime d'une modification / prorogation."""
    from app.services.payment_service import PaymentService, channel_for_payment_type

    if avenant.statut != STATUT_ATTENTE_PAIEMENT:
        raise AvenantError("Aucun complément de prime n'est attendu pour cette demande.")
    souscription = avenant.souscription or db.query(Souscription).get(avenant.souscription_id)
    amount = _dec(avenant.montant_ajustement)
    label = "Modification" if avenant.type_avenant == TYPE_MODIFICATION else "Prorogation"

    if settings.PAYMENT_SERVICE_MODE.lower() == "live" and channel_for_payment_type(payment_type):
        paiement, info = PaymentService.initiate_payment_intent(
            db=db,
            user=payer,
            subscription=souscription,
            amount=amount,
            payment_type=payment_type,
            flow=flow,
            description=f"{label} de la police {souscription.numero_souscription}",
            allow_active=True,
            before_commit=lambda p: setattr(avenant, "paiement_id", p.id),
        )
        return ActionResult(souscription, avenant=avenant, paiement=paiement, payment_info=info)

    paiement = Paiement(
        souscription_id=souscription.id,
        user_id=souscription.user_id,
        montant=amount,
        type_paiement=payment_type,
        statut=StatutPaiement.VALIDE,
        date_paiement=datetime.utcnow(),
        reference_transaction=f"TXN-{uuid.uuid4().hex[:16].upper()}",
    )
    db.add(paiement)
    db.flush()
    avenant.paiement_id = paiement.id
    finalize_avenant_payment(db, avenant, paiement)
    return ActionResult(souscription, avenant=avenant, paiement=paiement)


def abandon_pending(db: Session, avenant: Avenant, reason: Optional[str] = None) -> Avenant:
    if avenant.statut != STATUT_ATTENTE_PAIEMENT:
        raise AvenantError("Cette demande n'est plus en cours.")
    avenant.statut = STATUT_ABANDONNE
    avenant.notes = reason or avenant.notes
    db.flush()
    return avenant


def expire_stale_pending(db: Session, today: Optional[date] = None) -> int:
    """Abandonne les demandes dont la fenêtre est dépassée (modification après
    la date d'effet, prorogation après la fin de couverture initiale)."""
    day = _today(today)
    count = 0
    pendings = db.query(Avenant).filter(Avenant.statut == STATUT_ATTENTE_PAIEMENT).all()
    for avenant in pendings:
        souscription = avenant.souscription
        if souscription is None:
            continue
        expired = day > _as_date(souscription.date_fin)
        if expired:
            abandon_pending(db, avenant, "Complément non réglé dans le délai autorisé.")
            count += 1
    return count


# ---------------------------------------------------------------------------
# Ristournes (quittance 120)
# ---------------------------------------------------------------------------
def _create_ristourne(
    db: Session,
    souscription: Souscription,
    avenant: Avenant,
    paiement: Optional[Paiement],
    montants: Montants,
    *,
    motif: str,
) -> Ristourne:
    produit = getattr(souscription, "produit_assurance", None)
    ristourne = Ristourne(
        souscription_id=souscription.id,
        avenant_id=avenant.id,
        paiement_id=getattr(paiement, "id", None),
        statut=RISTOURNE_A_REMBOURSER,
        motif=motif,
        montant_prime=montants.prime,
        montant_frais_police=montants.frais_police,
        montant_taxes=montants.taxes + montants.frais_services,
        montant_total=montants.total,
        devise=getattr(produit, "currency", None) or "XAF",
    )
    db.add(ristourne)
    db.flush()
    return ristourne


def confirm_ristourne(
    db: Session,
    ristourne: Ristourne,
    actor: Optional[User],
    *,
    moyen_remboursement: str,
    reference: Optional[str] = None,
) -> Ristourne:
    """La finance MHC confirme le remboursement effectué → quittance de ristourne 120."""
    from app.services.mhc_reference_service import allocate_quittance_ristourne_number

    if ristourne.statut != RISTOURNE_A_REMBOURSER:
        raise AvenantError("Ce remboursement a déjà été confirmé.")
    moyen = (moyen_remboursement or "").strip().lower()
    if moyen not in RISTOURNE_MOYENS:
        raise AvenantError(f"Moyen de remboursement invalide. Valeurs : {', '.join(RISTOURNE_MOYENS)}.")
    ristourne.numero = allocate_quittance_ristourne_number(db)
    ristourne.statut = RISTOURNE_REMBOURSE
    ristourne.moyen_remboursement = moyen
    ristourne.reference_remboursement = (reference or "").strip() or None
    ristourne.confirmed_by_id = getattr(actor, "id", None)
    ristourne.confirmed_at = datetime.utcnow()
    paiement = ristourne.paiement
    if paiement is not None:
        paiement.montant_rembourse = _dec(paiement.montant_rembourse) + _dec(ristourne.montant_total)
    db.flush()
    souscription = ristourne.souscription or db.query(Souscription).get(ristourne.souscription_id)
    _notify(
        souscription,
        "Remboursement effectué",
        f"Le remboursement de {ristourne.montant_total} {ristourne.devise} est effectué. "
        "Votre quittance de ristourne est disponible.",
    )
    return ristourne


def build_ristourne_pdf(db: Session, ristourne: Ristourne) -> BytesIO:
    from app.services.official_travel_documents import generate_quittance_ristourne

    if ristourne.statut != RISTOURNE_REMBOURSE or not ristourne.numero:
        raise AvenantError("La quittance de ristourne est générée après confirmation du remboursement.")
    souscription = ristourne.souscription or db.query(Souscription).get(ristourne.souscription_id)
    user = db.query(User).filter(User.id == souscription.user_id).first()
    traveler_info, _ = _traveler_and_minors(db, souscription)
    return generate_quittance_ristourne(
        souscription,
        user,
        ristourne.numero,
        traveler_info=traveler_info,
        numero_avenant=ristourne.avenant.numero if ristourne.avenant else None,
        motif=ristourne.motif,
        montant_prime=ristourne.montant_prime,
        montant_frais_police=ristourne.montant_frais_police,
        montant_taxes=ristourne.montant_taxes,
        montant_total=ristourne.montant_total,
        devise=ristourne.devise,
        moyen_remboursement=ristourne.moyen_remboursement,
        date_emission=ristourne.confirmed_at,
    )


# ---------------------------------------------------------------------------
# PDF des avenants
# ---------------------------------------------------------------------------
def build_avenant_pdf(db: Session, avenant: Avenant) -> BytesIO:
    """(Re)génère le PDF d'un avenant émis."""
    from app.services.official_travel_documents import (
        generate_avenant_annulation,
        generate_avenant_modification,
        generate_avenant_prorogation,
    )

    if avenant.statut != STATUT_EMIS:
        raise AvenantError("L'avenant n'est généré qu'une fois la demande finalisée.")
    souscription = avenant.souscription or db.query(Souscription).get(avenant.souscription_id)
    if souscription is None:
        raise AvenantError("Souscription introuvable pour cet avenant.")
    user = db.query(User).filter(User.id == souscription.user_id).first()
    traveler_info, minors_info = _traveler_and_minors(db, souscription)
    common = {"traveler_info": traveler_info, "minors_info": minors_info}

    if avenant.type_avenant == TYPE_ANNULATION:
        return generate_avenant_annulation(souscription, user, avenant.numero, date_annulation=avenant.date_effet, **common)
    if avenant.type_avenant == TYPE_MODIFICATION:
        payload = avenant.payload or {}
        return generate_avenant_modification(
            souscription, user, avenant.numero,
            ancienne_destination=payload.get("ancienne_destination"),
            nouvelle_destination=payload.get("nouvelle_destination"),
            zone_tarifaire=payload.get("zone_tarifaire"),
            date_effet=avenant.date_effet,
            date_emission=avenant.created_at,
            **common,
        )
    if avenant.type_avenant == TYPE_PROROGATION:
        produit = getattr(souscription, "produit_assurance", None)
        return generate_avenant_prorogation(
            souscription, user, avenant.numero,
            date_fin_initiale=avenant.date_fin_initiale,
            nouvelle_date_fin=avenant.nouvelle_date_fin,
            date_effet=avenant.date_effet,
            prime_complementaire=avenant.montant_ajustement,
            devise=getattr(produit, "currency", None) or "XAF",
            date_emission=avenant.updated_at or avenant.created_at,
            **common,
        )
    raise AvenantError(f"Type d'avenant non pris en charge : {avenant.type_avenant}")


def get_avenant(db: Session, avenant_id: int) -> Optional[Avenant]:
    return db.query(Avenant).filter(Avenant.id == avenant_id).first()


def list_avenants(db: Session, souscription_id: int) -> list[Avenant]:
    return (
        db.query(Avenant)
        .filter(Avenant.souscription_id == souscription_id, Avenant.type_avenant.in_(ACTION_TYPES))
        .order_by(Avenant.created_at.desc())
        .all()
    )


def list_ristournes(db: Session, souscription_id: int) -> list[Ristourne]:
    return (
        db.query(Ristourne)
        .filter(Ristourne.souscription_id == souscription_id)
        .order_by(Ristourne.created_at.desc())
        .all()
    )
