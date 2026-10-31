"""Réclamations MyMHC (workflow V3 §8.1).

Statuts : Reçue → En analyse → Informations complémentaires requises → Traitée
(réponse motivée) → Clôturée. Contestation : demande de réexamen liée à la
réclamation initiale (historique conservé). Délais opérationnels par défaut :
première réponse 2 jours ouvrés, résolution 10 (15 si cas complexe).
Les urgences médicales relèvent du centre d'alerte (SOS), pas de la réclamation.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.reclamation import Reclamation, ReclamationEvent
from app.models.souscription import Souscription

logger = logging.getLogger(__name__)

CATEGORIES = {
    "qualite_service": "Qualité de service",
    "etablissement_partenaire": "Établissement partenaire",
    "decision_couverture": "Décision de couverture",
    "paiement_remboursement": "Paiement / remboursement",
    "modification_infos": "Modification de mes informations personnelles",
    "application": "Application MyMHC",
    "autre": "Autre",
}

STATUT_RECUE = "recue"
STATUT_EN_ANALYSE = "en_analyse"
STATUT_INFOS_REQUISES = "infos_requises"
STATUT_TRAITEE = "traitee"
STATUT_CLOTUREE = "cloturee"
STATUTS = {
    STATUT_RECUE: "Reçue",
    STATUT_EN_ANALYSE: "En analyse",
    STATUT_INFOS_REQUISES: "Informations complémentaires requises",
    STATUT_TRAITEE: "Traitée",
    STATUT_CLOTUREE: "Clôturée",
}
TRANSITIONS = {
    STATUT_RECUE: {STATUT_EN_ANALYSE, STATUT_INFOS_REQUISES, STATUT_TRAITEE},
    STATUT_EN_ANALYSE: {STATUT_INFOS_REQUISES, STATUT_TRAITEE},
    STATUT_INFOS_REQUISES: {STATUT_EN_ANALYSE, STATUT_TRAITEE},
    STATUT_TRAITEE: {STATUT_CLOTUREE, STATUT_EN_ANALYSE},
    STATUT_CLOTUREE: set(),
}

DELAI_PREMIERE_REPONSE_JOURS = 2
DELAI_RESOLUTION_JOURS = 10
DELAI_RESOLUTION_COMPLEXE_JOURS = 15
MAX_PIECES_JOINTES = 5
MAX_PIECE_BYTES = 5 * 1024 * 1024

URGENCE_MESSAGE = (
    "Pour une urgence médicale, utilisez le bouton SOS : le centre d'alerte/assistance "
    "vous prend en charge immédiatement. La réclamation n'est pas adaptée aux urgences."
)


def add_business_days(start: datetime, days: int) -> datetime:
    current = start
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


def _next_reference(db: Session, now: datetime) -> str:
    count = db.query(Reclamation).count() + 1
    while True:
        reference = f"REC-{now:%Y}-{count:06d}"
        if not db.query(Reclamation.id).filter(Reclamation.reference == reference).first():
            return reference
        count += 1


def _notify(reclamation: Reclamation, titre: str, message: str) -> None:
    try:
        from app.services.notification_service import NotificationService

        NotificationService.create_notification(
            user_id=reclamation.user_id,
            type_notification="reclamation_update",
            titre=titre,
            message=message,
            lien_relation_id=reclamation.id,
            lien_relation_type="reclamation",
            channels=["push"],
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("Notification réclamation %s impossible: %s", reclamation.reference, exc)


def _validate_attachments(pieces: Optional[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    import base64

    cleaned = []
    for piece in pieces or []:
        nom = str(piece.get("nom") or "piece-jointe")[:150]
        data_url = str(piece.get("data_url") or "")
        header, sep, b64 = data_url.partition(",")
        if not sep or not header.startswith("data:"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Pièce jointe invalide : {nom}")
        try:
            size = len(base64.b64decode(b64, validate=True))
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Pièce jointe illisible : {nom}")
        if size > MAX_PIECE_BYTES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Pièce jointe trop volumineuse (5 Mo max) : {nom}")
        cleaned.append({"nom": nom, "data_url": data_url, "taille": size})
    if len(cleaned) > MAX_PIECES_JOINTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{MAX_PIECES_JOINTES} pièces jointes maximum.")
    return cleaned


def _event(db: Session, reclamation: Reclamation, type_event: str, *, auteur_id: Optional[int],
           statut: Optional[str] = None, message: Optional[str] = None, visible: bool = True) -> None:
    db.add(ReclamationEvent(
        reclamation_id=reclamation.id,
        auteur_id=auteur_id,
        type_event=type_event,
        statut=statut,
        message=message,
        visible_assure=visible,
    ))


def create_reclamation(
    db: Session,
    user,
    *,
    categorie: str,
    objet: str,
    description: str,
    souscription_id: Optional[int] = None,
    personne_concernee: Optional[str] = None,
    pieces_jointes: Optional[list[dict[str, Any]]] = None,
    parent: Optional[Reclamation] = None,
) -> Reclamation:
    categorie = (categorie or "").strip()
    if categorie not in CATEGORIES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Catégorie de réclamation invalide.")
    objet = (objet or "").strip()
    description = (description or "").strip()
    if not objet or not description:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="L'objet et la description sont obligatoires.")
    if souscription_id is not None:
        owned = (
            db.query(Souscription.id)
            .filter(Souscription.id == souscription_id, Souscription.user_id == user.id)
            .first()
        )
        if not owned:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrat introuvable.")
    now = datetime.utcnow()
    reclamation = Reclamation(
        reference=_next_reference(db, now),
        user_id=user.id,
        categorie=categorie,
        objet=objet[:200],
        description=description,
        souscription_id=souscription_id,
        personne_concernee=(personne_concernee or "").strip() or None,
        pieces_jointes=_validate_attachments(pieces_jointes),
        coordonnees={
            "nom": getattr(user, "full_name", None),
            "email": getattr(user, "email", None),
            "telephone": getattr(user, "telephone", None),
        },
        statut=STATUT_RECUE,
        parent_id=getattr(parent, "id", None),
        echeance_premiere_reponse=add_business_days(now, DELAI_PREMIERE_REPONSE_JOURS),
        echeance_resolution=add_business_days(now, DELAI_RESOLUTION_JOURS),
    )
    db.add(reclamation)
    db.flush()
    _event(db, reclamation, "contestation" if parent else "creation", auteur_id=user.id, statut=STATUT_RECUE,
           message=f"Demande de réexamen de la réclamation {parent.reference}" if parent else None)
    db.commit()
    db.refresh(reclamation)
    _notify(
        reclamation,
        "Réclamation reçue",
        f"Votre réclamation {reclamation.reference} a bien été enregistrée. "
        f"Première réponse sous {DELAI_PREMIERE_REPONSE_JOURS} jours ouvrés.",
    )
    return reclamation


def add_user_message(db: Session, reclamation: Reclamation, user, message: str) -> Reclamation:
    message = (message or "").strip()
    if not message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le message ne peut pas être vide.")
    if reclamation.statut == STATUT_CLOTUREE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Réclamation clôturée : utilisez la contestation.")
    _event(db, reclamation, "message", auteur_id=user.id, message=message)
    if reclamation.statut == STATUT_INFOS_REQUISES:
        reclamation.statut = STATUT_EN_ANALYSE
        _event(db, reclamation, "statut", auteur_id=user.id, statut=STATUT_EN_ANALYSE,
               message="Informations complémentaires transmises")
    db.commit()
    db.refresh(reclamation)
    return reclamation


def contest(db: Session, reclamation: Reclamation, user, motif: str) -> Reclamation:
    if reclamation.statut not in {STATUT_TRAITEE, STATUT_CLOTUREE}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contestation est possible une fois la réclamation traitée.",
        )
    # Contestation possible uniquement dans le mois qui suit la clôture (§3.11).
    ref = reclamation.cloturee_at or reclamation.traitee_at
    if ref is not None:
        ref_date = ref.date() if hasattr(ref, "date") else ref
        if (datetime.utcnow().date() - ref_date).days > 31:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le délai de contestation (1 mois après la clôture) est dépassé.",
            )
    return create_reclamation(
        db,
        user,
        categorie=reclamation.categorie,
        objet=f"Réexamen — {reclamation.objet}"[:200],
        description=(motif or "").strip(),
        souscription_id=reclamation.souscription_id,
        personne_concernee=reclamation.personne_concernee,
        parent=reclamation,
    )


def change_status(
    db: Session,
    reclamation: Reclamation,
    agent,
    *,
    statut: str,
    message: Optional[str] = None,
    complexe: Optional[bool] = None,
) -> Reclamation:
    if statut not in STATUTS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Statut inconnu.")
    if statut not in TRANSITIONS.get(reclamation.statut, set()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transition impossible : {STATUTS[reclamation.statut]} → {STATUTS[statut]}.",
        )
    message = (message or "").strip() or None
    if statut in {STATUT_TRAITEE, STATUT_INFOS_REQUISES} and not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Une réponse motivée est requise." if statut == STATUT_TRAITEE else "Précisez les informations demandées.",
        )
    now = datetime.utcnow()
    if complexe is not None and complexe != reclamation.complexe:
        reclamation.complexe = complexe
        jours = DELAI_RESOLUTION_COMPLEXE_JOURS if complexe else DELAI_RESOLUTION_JOURS
        reclamation.echeance_resolution = add_business_days(reclamation.created_at or now, jours)
    reclamation.statut = statut
    reclamation.assigned_to_id = reclamation.assigned_to_id or getattr(agent, "id", None)
    if reclamation.premiere_reponse_at is None:
        reclamation.premiere_reponse_at = now
    if statut == STATUT_TRAITEE:
        reclamation.reponse = message
        reclamation.traitee_at = now
    if statut == STATUT_CLOTUREE:
        reclamation.cloturee_at = now
    _event(db, reclamation, "statut", auteur_id=getattr(agent, "id", None), statut=statut, message=message)
    db.commit()
    db.refresh(reclamation)
    _notify(
        reclamation,
        f"Réclamation {reclamation.reference} : {STATUTS[statut]}",
        "Consultez le détail de votre réclamation dans la rubrique Aide.",
    )
    return reclamation


def serialize(reclamation: Reclamation, *, staff: bool = False) -> dict[str, Any]:
    return {
        "id": reclamation.id,
        "reference": reclamation.reference,
        "categorie": reclamation.categorie,
        "categorie_libelle": CATEGORIES.get(reclamation.categorie, reclamation.categorie),
        "objet": reclamation.objet,
        "description": reclamation.description,
        "souscription_id": reclamation.souscription_id,
        "personne_concernee": reclamation.personne_concernee,
        "pieces_jointes": [{"nom": p.get("nom"), "taille": p.get("taille")} for p in (reclamation.pieces_jointes or [])],
        "coordonnees": reclamation.coordonnees,
        "statut": reclamation.statut,
        "statut_libelle": STATUTS.get(reclamation.statut, reclamation.statut),
        "reponse": reclamation.reponse,
        "complexe": bool(reclamation.complexe),
        "parent_id": reclamation.parent_id,
        "echeance_premiere_reponse": reclamation.echeance_premiere_reponse,
        "echeance_resolution": reclamation.echeance_resolution,
        "premiere_reponse_at": reclamation.premiere_reponse_at,
        "traitee_at": reclamation.traitee_at,
        "cloturee_at": reclamation.cloturee_at,
        "created_at": reclamation.created_at,
        "user_id": reclamation.user_id if staff else None,
        "historique": [
            {
                "type": e.type_event,
                "statut": e.statut,
                "statut_libelle": STATUTS.get(e.statut) if e.statut else None,
                "message": e.message,
                "auteur_est_assure": e.auteur_id == reclamation.user_id,
                "date": e.created_at,
            }
            for e in reclamation.events
            if staff or e.visible_assure
        ],
    }
