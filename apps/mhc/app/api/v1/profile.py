"""Profil MyMHC (workflow V3 §3.3, §4.3) : demandes de modification validées par MHC
et enfants bénéficiaires gérés par le parent."""
from datetime import date, datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session, undefer

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.core.permissions import is_internal_backoffice_role
from app.models.profile_change import EnfantBeneficiaire, ProfileChangeRequest
from app.models.user import User

router = APIRouter()

# Champs d'identité : validation MHC requise ; nom / naissance / pièce exigent une pièce d'identité.
IDENTITY_FIELDS = {
    "full_name": "Nom et prénom",
    "date_naissance": "Date de naissance",
    "nationalite": "Nationalité",
    "pays_residence": "Pays de résidence",
    "numero_passeport": "Numéro de pièce d'identité",
    "validite_passeport": "Validité de la pièce d'identité",
}
FIELDS_REQUIRING_ID_DOCUMENT = {"full_name", "date_naissance", "numero_passeport", "validite_passeport"}
DATE_FIELDS = {"date_naissance", "validite_passeport"}
MAX_DOC_BYTES = 5 * 1024 * 1024


def _role(user) -> str:
    role = getattr(user, "role", None)
    return str(getattr(role, "value", role) or "user")


def _require_staff(user) -> None:
    if not is_internal_backoffice_role(_role(user)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux profils MHC internes.")


def _parse_date(value: Any, label: str) -> date:
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{label} invalide (AAAA-MM-JJ).")


def _check_data_url(data_url: Optional[str], label: str) -> Optional[str]:
    if not data_url:
        return None
    import base64

    header, sep, b64 = data_url.partition(",")
    if not sep or not header.startswith("data:"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{label} : fichier invalide.")
    try:
        size = len(base64.b64decode(b64, validate=True))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{label} : fichier illisible.")
    if size > MAX_DOC_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{label} : 5 Mo maximum.")
    return data_url


def mask_document_number(numero: Optional[str]) -> Optional[str]:
    """Numéro de pièce masqué à l'affichage (seuls les 3 derniers caractères visibles)."""
    if not numero:
        return numero
    numero = str(numero)
    return "•" * max(len(numero) - 3, 0) + numero[-3:]


# ---------------------------------------------------------------------------
# Demandes de modification du profil
# ---------------------------------------------------------------------------
class ProfileChangeCreate(BaseModel):
    champs: dict[str, Any]
    piece_identite_nom: Optional[str] = None
    piece_identite_data_url: Optional[str] = None


class ProfileChangeDecision(BaseModel):
    approved: bool
    motif: Optional[str] = None


def _serialize_request(req: ProfileChangeRequest, *, staff: bool = False) -> dict[str, Any]:
    champs = dict(req.champs or {})
    if not staff and champs.get("numero_passeport"):
        champs["numero_passeport"] = mask_document_number(champs["numero_passeport"])
    data = {
        "id": req.id,
        "user_id": req.user_id,
        "champs": champs,
        "libelles": {k: IDENTITY_FIELDS.get(k, k) for k in champs},
        "statut": req.statut,
        "motif_refus": req.motif_refus,
        "decided_at": req.decided_at,
        "created_at": req.created_at,
    }
    if staff:
        data["anciennes_valeurs"] = req.anciennes_valeurs
        piece = req.piece_identite or {}
        data["piece_identite"] = {"nom": piece.get("nom"), "data_url": piece.get("data_url")} if piece else None
        user = req.user
        data["assure"] = {"nom": getattr(user, "full_name", None), "email": getattr(user, "email", None)}
    return data


def _notify(user_id: int, titre: str, message: str, request_id: int) -> None:
    try:
        from app.services.notification_service import NotificationService

        NotificationService.create_notification(
            user_id=user_id,
            type_notification="account_profile_change",
            titre=titre,
            message=message,
            lien_relation_id=request_id,
            lien_relation_type="profile_change",
            channels=["push"],
        )
    except Exception:  # pragma: no cover
        pass


@router.post("/profile-change-requests", status_code=status.HTTP_201_CREATED)
async def create_profile_change_request(
    body: ProfileChangeCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    champs = {k: (str(v).strip() if v is not None else None) for k, v in (body.champs or {}).items()}
    unknown = set(champs) - set(IDENTITY_FIELDS)
    if unknown:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Champs non concernés : {', '.join(sorted(unknown))}")
    champs = {k: v for k, v in champs.items() if v}
    if not champs:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Aucune modification demandée.")
    for field in DATE_FIELDS & set(champs):
        champs[field] = _parse_date(champs[field], IDENTITY_FIELDS[field]).isoformat()
    piece = _check_data_url(body.piece_identite_data_url, "Pièce d'identité")
    if FIELDS_REQUIRING_ID_DOCUMENT & set(champs) and not piece:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Une pièce d'identité est requise pour modifier le nom, la date de naissance ou la pièce d'identité.",
        )
    pending = (
        db.query(ProfileChangeRequest.id)
        .filter(ProfileChangeRequest.user_id == current_user.id, ProfileChangeRequest.statut == "pending")
        .first()
    )
    if pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Une demande de modification est déjà en attente de validation.")
    user = db.query(User).filter(User.id == current_user.id).first()
    anciennes = {k: (getattr(user, k).isoformat() if hasattr(getattr(user, k), "isoformat") else getattr(user, k)) for k in champs}
    req = ProfileChangeRequest(
        user_id=user.id,
        champs=champs,
        anciennes_valeurs=anciennes,
        piece_identite={"nom": body.piece_identite_nom or "piece-identite", "data_url": piece} if piece else None,
        statut="pending",
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return _serialize_request(req)


@router.get("/profile-change-requests/me")
async def list_my_profile_change_requests(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    rows = (
        db.query(ProfileChangeRequest)
        .filter(ProfileChangeRequest.user_id == current_user.id)
        .order_by(ProfileChangeRequest.created_at.desc())
        .all()
    )
    return [_serialize_request(r) for r in rows]


@router.get("/profile-change-requests")
async def list_profile_change_requests(
    statut: Optional[str] = "pending",
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_staff(current_user)
    query = db.query(ProfileChangeRequest).options(undefer(ProfileChangeRequest.piece_identite))
    if statut:
        query = query.filter(ProfileChangeRequest.statut == statut)
    return [_serialize_request(r, staff=True) for r in query.order_by(ProfileChangeRequest.created_at.asc()).limit(500).all()]


@router.post("/profile-change-requests/{request_id}/decision")
async def decide_profile_change_request(
    request_id: int,
    body: ProfileChangeDecision,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_staff(current_user)
    req = db.query(ProfileChangeRequest).filter(ProfileChangeRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande introuvable.")
    if req.statut != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cette demande a déjà été traitée.")
    motif = (body.motif or "").strip() or None
    if not body.approved and not motif:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le motif du refus est obligatoire.")
    req.decided_by_id = current_user.id
    req.decided_at = datetime.utcnow()
    if body.approved:
        # Mise à jour du profil uniquement : pas de changement rétroactif des polices actives.
        user = db.query(User).filter(User.id == req.user_id).first()
        for field, value in (req.champs or {}).items():
            setattr(user, field, _parse_date(value, IDENTITY_FIELDS[field]) if field in DATE_FIELDS else value)
        req.statut = "approved"
        titre, message = "Modification du profil validée", "Votre demande de modification du profil a été validée par MHC."
    else:
        req.statut = "rejected"
        req.motif_refus = motif
        titre = "Modification du profil refusée"
        message = f"Votre demande de modification du profil a été refusée. Motif : {motif}. Vos données actuelles sont conservées."
    db.commit()
    db.refresh(req)
    _notify(req.user_id, titre, message, req.id)
    return _serialize_request(req, staff=True)


# ---------------------------------------------------------------------------
# Enfants bénéficiaires
# ---------------------------------------------------------------------------
class EnfantBody(BaseModel):
    nom: str
    prenom: Optional[str] = None
    date_naissance: str
    nationalite: Optional[str] = None
    numero_piece: Optional[str] = None
    validite_piece: Optional[str] = None
    lien_parente: Optional[str] = None
    photo_data_url: Optional[str] = None
    copie_piece_data_url: Optional[str] = None


def _serialize_enfant(e: EnfantBeneficiaire) -> dict[str, Any]:
    return {
        "id": e.id,
        "nom": e.nom,
        "prenom": e.prenom,
        "date_naissance": e.date_naissance.isoformat() if e.date_naissance else None,
        "nationalite": e.nationalite,
        "numero_piece": e.numero_piece,
        "numero_piece_masque": mask_document_number(e.numero_piece),
        "validite_piece": e.validite_piece.isoformat() if e.validite_piece else None,
        "lien_parente": e.lien_parente,
        "a_photo": bool(e.photo),
        "a_copie_piece": bool(e.copie_piece),
        "photo_data_url": e.photo,
        "copie_piece_data_url": e.copie_piece,
    }


def _owned_enfant(db: Session, enfant_id: int, user) -> EnfantBeneficiaire:
    enfant = (
        db.query(EnfantBeneficiaire)
        .options(undefer(EnfantBeneficiaire.photo), undefer(EnfantBeneficiaire.copie_piece))
        .filter(EnfantBeneficiaire.id == enfant_id, EnfantBeneficiaire.parent_id == user.id, EnfantBeneficiaire.actif == True)  # noqa: E712
        .first()
    )
    if not enfant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enfant introuvable.")
    return enfant


def _apply_enfant(enfant: EnfantBeneficiaire, body: EnfantBody) -> None:
    born = _parse_date(body.date_naissance, "Date de naissance")
    today = date.today()
    age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    if born > today or age >= 18:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Un enfant bénéficiaire doit avoir moins de 18 ans.")
    enfant.nom = body.nom.strip()
    enfant.prenom = (body.prenom or "").strip() or None
    enfant.date_naissance = born
    enfant.nationalite = (body.nationalite or "").strip() or None
    enfant.numero_piece = (body.numero_piece or "").strip() or None
    enfant.validite_piece = _parse_date(body.validite_piece, "Validité de la pièce") if body.validite_piece else None
    enfant.lien_parente = (body.lien_parente or "").strip() or None
    if body.photo_data_url is not None:
        enfant.photo = _check_data_url(body.photo_data_url, "Photo")
    if body.copie_piece_data_url is not None:
        enfant.copie_piece = _check_data_url(body.copie_piece_data_url, "Copie de la pièce")


@router.get("/users/me/enfants")
async def list_my_children(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    rows = (
        db.query(EnfantBeneficiaire)
        .options(undefer(EnfantBeneficiaire.photo), undefer(EnfantBeneficiaire.copie_piece))
        .filter(EnfantBeneficiaire.parent_id == current_user.id, EnfantBeneficiaire.actif == True)  # noqa: E712
        .order_by(EnfantBeneficiaire.date_naissance.desc())
        .all()
    )
    return [_serialize_enfant(e) for e in rows]


@router.post("/users/me/enfants", status_code=status.HTTP_201_CREATED)
async def create_child(body: EnfantBody, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    enfant = EnfantBeneficiaire(parent_id=current_user.id)
    _apply_enfant(enfant, body)
    db.add(enfant)
    db.commit()
    db.refresh(enfant)
    return _serialize_enfant(enfant)


@router.put("/users/me/enfants/{enfant_id}")
async def update_child(enfant_id: int, body: EnfantBody, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    enfant = _owned_enfant(db, enfant_id, current_user)
    _apply_enfant(enfant, body)
    db.commit()
    db.refresh(enfant)
    return _serialize_enfant(enfant)


@router.delete("/users/me/enfants/{enfant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_child(enfant_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Retire l'enfant du compte (désactivation ; les polices existantes ne sont pas modifiées)."""
    enfant = _owned_enfant(db, enfant_id, current_user)
    enfant.actif = False
    db.commit()
    return None
