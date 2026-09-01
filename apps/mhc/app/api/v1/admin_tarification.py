"""Admin : référentiels de tarification (zones, fenêtres durée, tranches âge)."""
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.core.enums import Role
from app.models.user import User
from app.models.destination import DestinationCountry
from app.models.tarification import (
    TarificationFenetreDuree,
    TarificationGrilleFinale,
    TarificationGrillePrix,
    TarificationTrancheAge,
    TarificationZone,
    TarificationZonePays,
)
from app.schemas.tarification import (
    CanonicalVoyageZoneItem,
    CanonicalVoyageZonesResponse,
    TarificationFenetreDureeCreate,
    TarificationFenetreDureeResponse,
    TarificationFenetreDureeUpdate,
    TarificationGrilleFinaleListResponse,
    TarificationGrilleFinaleRowResponse,
    TarificationGrilleFinaleUpsert,
    TarificationGrilleMatrixResponse,
    TarificationGrillePrixCellResponse,
    TarificationGrillePrixUpsert,
    TarificationTrancheAgeCreate,
    TarificationTrancheAgeResponse,
    TarificationTrancheAgeUpdate,
    TarificationZoneCreate,
    TarificationZoneDetailResponse,
    TarificationZonePaysUpdate,
    TarificationZoneResponse,
    TarificationZoneUpdate,
)
from app.services.voyage_premium_calculator import (
    CANONICAL_ZONE_DESCRIPTIONS_FR,
    ZONES_CANONIQUES,
)

router = APIRouter()

_FORM_ALIGNMENT_HINT = (
    "Les pays proposés dans les parcours souscription proviennent du référentiel Destinations "
    "(champ « nom », identique au libellé des listes). Rattachez chaque pays actif à une zone "
    "dont le code correspond exactement à l’une des valeurs ci-dessous pour que le devis utilise "
    "la grille tarifaire voyage. Un même pays ne peut être que dans une seule zone."
)


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin role required.",
        )
    return current_user


def _grille_finale_row_to_response(cell: TarificationGrilleFinale) -> TarificationGrilleFinaleRowResponse:
    z = cell.zone
    f = cell.fenetre
    t = cell.tranche_age
    return TarificationGrilleFinaleRowResponse(
        id=cell.id,
        produit_assurance_id=cell.produit_assurance_id,
        zone_id=cell.zone_id,
        zone_code=z.code if z else "",
        zone_nom=z.nom if z else "",
        fenetre_duree_id=cell.fenetre_duree_id,
        fenetre_libelle=f.libelle if f else None,
        duree_min_jours=f.duree_min_jours if f else 0,
        duree_max_jours=f.duree_max_jours if f else 0,
        tranche_age_id=cell.tranche_age_id,
        tranche_libelle=t.libelle if t else None,
        tranche_age_min=t.age_min if t else None,
        tranche_age_max=t.age_max if t else None,
        coefficient_age=cell.coefficient_age,
        tarif_final=cell.tarif_final,
        created_at=cell.created_at,
        updated_at=cell.updated_at,
    )


def _zone_to_detail(db: Session, z: TarificationZone) -> TarificationZoneDetailResponse:
    ids = [
        row.destination_country_id
        for row in db.query(TarificationZonePays)
        .filter(TarificationZonePays.zone_id == z.id)
        .all()
    ]
    base = TarificationZoneResponse.model_validate(z)
    return TarificationZoneDetailResponse(
        **base.model_dump(),
        destination_country_ids=ids,
    )


@router.get(
    "/canonical-voyage-zones",
    response_model=CanonicalVoyageZonesResponse,
    summary="Zones canoniques grille voyage (alignement pays)",
)
def get_canonical_voyage_zones(
    _: User = Depends(require_admin),
):
    """
    Liste les codes de zone attendus par le moteur `voyage_grille_json` (grille JSON).
    À utiliser pour vérifier que `tarification_zones.code` et `tarification_zone_pays` sont alignés.
    """
    items = [
        CanonicalVoyageZoneItem(
            code=code,
            description=CANONICAL_ZONE_DESCRIPTIONS_FR.get(code, ""),
        )
        for code in sorted(ZONES_CANONIQUES)
    ]
    return CanonicalVoyageZonesResponse(
        zones=items,
        form_alignment_hint=_FORM_ALIGNMENT_HINT,
    )


@router.get(
    "/voyage-reference",
    summary="Grille nationale primes + surprimes (référence devis)",
)
def get_voyage_reference_tarifs(_: User = Depends(require_admin)):
    """
    Données affichées en admin : primes FCFA communes à tous les produits (grille JSON moteur)
    et % de surprime âge par défaut (si champs produit non renseignés).
    """
    from decimal import Decimal

    from app.core.tarification_defaults import (
        DEFAULT_SURPRIME_70_75_PCT,
        DEFAULT_SURPRIME_76_80_PCT,
        DEFAULT_SURPRIME_81_89_PCT,
        DEFAULT_SURPRIME_MOINS_18_PCT,
        DURATION_BAND_LABELS_FR,
        FRAIS_SERVICES_SUR_PRIME_PCT,
        ZONE_ROW_LABELS_FR,
    )
    from app.services.voyage_premium_calculator import (
        GRILLE_TARIFAIRE_BASE,
        TRANCHES_DUREE,
    )

    zones_order = list(GRILLE_TARIFAIRE_BASE.keys())
    duration_bands = [
        {
            "code": code,
            "min_jours": lo,
            "max_jours": hi,
            "label_fr": DURATION_BAND_LABELS_FR.get(code, f"{lo} à {hi} jours"),
        }
        for code, lo, hi in TRANCHES_DUREE
    ]
    primes_fcfa = {
        z: {k: int(v) for k, v in GRILLE_TARIFAIRE_BASE[z].items()}
        for z in zones_order
    }
    # Indicatif 18–69 ans (sans surprime) : frais = 15 % de la prime grille
    frais_fcfa = {
        z: {
            k: int(
                (
                    Decimal(primes_fcfa[z][k]) * FRAIS_SERVICES_SUR_PRIME_PCT / Decimal("100")
                ).quantize(Decimal("1"))
            )
            for k in primes_fcfa[z]
        }
        for z in zones_order
    }
    return {
        "currency": "XAF",
        "currency_label": "FCFA",
        "zones_order": zones_order,
        "zone_row_labels_fr": {k: ZONE_ROW_LABELS_FR.get(k, k) for k in zones_order},
        "duration_bands": duration_bands,
        "primes_fcfa_by_zone": primes_fcfa,
        "frais_fcfa_by_zone": frais_fcfa,
        "frais_sur_prime_pct": str(FRAIS_SERVICES_SUR_PRIME_PCT),
        "default_surprimes_pct": {
            "moins_18": str(DEFAULT_SURPRIME_MOINS_18_PCT),
            "70_75": str(DEFAULT_SURPRIME_70_75_PCT),
            "76_80": str(DEFAULT_SURPRIME_76_80_PCT),
            "81_89": str(DEFAULT_SURPRIME_81_89_PCT),
        },
        "surprime_labels_fr": [
            {"tranche": "Enfant de moins de 18 ans", "pct": str(DEFAULT_SURPRIME_MOINS_18_PCT)},
            {"tranche": "Séniors 70 à 75 ans", "pct": str(DEFAULT_SURPRIME_70_75_PCT)},
            {"tranche": "Séniors 76 à 80 ans", "pct": str(DEFAULT_SURPRIME_76_80_PCT)},
            {"tranche": "Séniors 81 à 89 ans (et 90+)", "pct": str(DEFAULT_SURPRIME_81_89_PCT)},
        ],
        "reference_18_69": (
            f"0 % de surprime ; frais de services = {FRAIS_SERVICES_SUR_PRIME_PCT} % de la prime "
            "(après surprime le cas échéant)"
        ),
        "engine_note": (
            "Zone tarifaire = parcours pays de résidence → pays de destination. "
            "Frais de services = pourcentage fixe de la prime après surprime âge (voir frais_sur_prime_pct). "
            "Le tableau admin des frais est indicatif pour 18–69 ans sans surprime. "
            "Produits avec matrice `produit_prime_tarif` : logique inchangée."
        ),
    }


# ---------- Zones ----------
@router.get("/zones", response_model=List[TarificationZoneDetailResponse])
def list_zones(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    zones = (
        db.query(TarificationZone)
        .order_by(TarificationZone.ordre_affichage.desc(), TarificationZone.nom)
        .all()
    )
    return [_zone_to_detail(db, z) for z in zones]


@router.post("/zones", response_model=TarificationZoneDetailResponse, status_code=status.HTTP_201_CREATED)
def create_zone(
    data: TarificationZoneCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    code = (data.code or "").strip().upper()
    if db.query(TarificationZone).filter(TarificationZone.code == code).first():
        raise HTTPException(status_code=400, detail="Ce code de zone existe déjà")
    now = datetime.utcnow()
    z = TarificationZone(
        code=code,
        nom=data.nom.strip(),
        description=(data.description or "").strip() or None,
        coefficient=data.coefficient,
        ordre_affichage=data.ordre_affichage,
        est_actif=data.est_actif,
        created_at=now,
        updated_at=now,
    )
    db.add(z)
    db.commit()
    db.refresh(z)
    return _zone_to_detail(db, z)


@router.put("/zones/{zone_id}", response_model=TarificationZoneDetailResponse)
def update_zone(
    zone_id: int,
    data: TarificationZoneUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    z = db.query(TarificationZone).filter(TarificationZone.id == zone_id).first()
    if not z:
        raise HTTPException(status_code=404, detail="Zone introuvable")
    payload = data.model_dump(exclude_unset=True)
    if "code" in payload and payload["code"] is not None:
        payload["code"] = str(payload["code"]).strip().upper()
        other = (
            db.query(TarificationZone)
            .filter(
                TarificationZone.code == payload["code"],
                TarificationZone.id != zone_id,
            )
            .first()
        )
        if other:
            raise HTTPException(status_code=400, detail="Ce code de zone existe déjà")
    for k, v in payload.items():
        setattr(z, k, v)
    z.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(z)
    return _zone_to_detail(db, z)


@router.delete("/zones/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_zone(
    zone_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    z = db.query(TarificationZone).filter(TarificationZone.id == zone_id).first()
    if not z:
        raise HTTPException(status_code=404, detail="Zone introuvable")
    # Supprimer d’abord les lignes liées : sans cascade ORM explicite, SQLAlchemy
    # tentait de mettre zone_id à NULL (NOT NULL → 500).
    db.query(TarificationGrilleFinale).filter(
        TarificationGrilleFinale.zone_id == zone_id
    ).delete(synchronize_session=False)
    db.query(TarificationGrillePrix).filter(TarificationGrillePrix.zone_id == zone_id).delete(
        synchronize_session=False
    )
    db.query(TarificationZonePays).filter(TarificationZonePays.zone_id == zone_id).delete(
        synchronize_session=False
    )
    db.delete(z)
    db.commit()
    return None


@router.put("/zones/{zone_id}/pays", response_model=TarificationZoneDetailResponse)
def set_zone_countries(
    zone_id: int,
    body: TarificationZonePaysUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    z = db.query(TarificationZone).filter(TarificationZone.id == zone_id).first()
    if not z:
        raise HTTPException(status_code=404, detail="Zone introuvable")
    country_ids = sorted({int(x) for x in body.destination_country_ids})
    for cid in country_ids:
        if not db.query(DestinationCountry).filter(DestinationCountry.id == cid).first():
            raise HTTPException(status_code=400, detail=f"Pays destination inconnu: {cid}")
    # Un pays peut être dans plusieurs zones (ex. INTRA + INTER). On ne modifie que cette zone.
    db.query(TarificationZonePays).filter(TarificationZonePays.zone_id == zone_id).delete(
        synchronize_session=False
    )
    db.flush()
    now = datetime.utcnow()
    for cid in country_ids:
        db.add(
            TarificationZonePays(
                zone_id=zone_id,
                destination_country_id=cid,
                created_at=now,
                updated_at=now,
            )
        )
    db.commit()
    db.refresh(z)
    return _zone_to_detail(db, z)


# ---------- Fenêtres durée ----------
@router.get("/fenetres-duree", response_model=List[TarificationFenetreDureeResponse])
def list_fenetres_duree(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    rows = (
        db.query(TarificationFenetreDuree)
        .order_by(
            TarificationFenetreDuree.ordre_priorite.desc(),
            TarificationFenetreDuree.duree_min_jours,
        )
        .all()
    )
    return rows


@router.post(
    "/fenetres-duree",
    response_model=TarificationFenetreDureeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_fenetre_duree(
    data: TarificationFenetreDureeCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    if data.duree_min_jours > data.duree_max_jours:
        raise HTTPException(status_code=400, detail="duree_min_jours > duree_max_jours")
    now = datetime.utcnow()
    row = TarificationFenetreDuree(
        libelle=(data.libelle or "").strip() or None,
        duree_min_jours=data.duree_min_jours,
        duree_max_jours=data.duree_max_jours,
        coefficient=data.coefficient,
        ordre_priorite=data.ordre_priorite,
        est_actif=data.est_actif,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/fenetres-duree/{fenetre_id}", response_model=TarificationFenetreDureeResponse)
def update_fenetre_duree(
    fenetre_id: int,
    data: TarificationFenetreDureeUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    row = (
        db.query(TarificationFenetreDuree)
        .filter(TarificationFenetreDuree.id == fenetre_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Fenêtre introuvable")
    payload = data.model_dump(exclude_unset=True)
    dmin = payload.get("duree_min_jours", row.duree_min_jours)
    dmax = payload.get("duree_max_jours", row.duree_max_jours)
    if dmin > dmax:
        raise HTTPException(status_code=400, detail="duree_min_jours > duree_max_jours")
    for k, v in payload.items():
        setattr(row, k, v)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row


@router.delete("/fenetres-duree/{fenetre_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fenetre_duree(
    fenetre_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    row = (
        db.query(TarificationFenetreDuree)
        .filter(TarificationFenetreDuree.id == fenetre_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Fenêtre introuvable")
    # Éviter UPDATE fenetre_duree_id=NULL (NOT NULL) : supprimer d’abord les lignes liées.
    db.query(TarificationGrilleFinale).filter(
        TarificationGrilleFinale.fenetre_duree_id == fenetre_id
    ).delete(synchronize_session=False)
    db.query(TarificationGrillePrix).filter(
        TarificationGrillePrix.fenetre_duree_id == fenetre_id
    ).delete(synchronize_session=False)
    db.delete(row)
    db.commit()
    return None


# ---------- Tranches âge ----------
@router.get("/tranches-age", response_model=List[TarificationTrancheAgeResponse])
def list_tranches_age(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    rows = (
        db.query(TarificationTrancheAge)
        .order_by(
            TarificationTrancheAge.ordre_priorite.desc(),
            TarificationTrancheAge.id,
        )
        .all()
    )
    return rows


@router.post(
    "/tranches-age",
    response_model=TarificationTrancheAgeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_tranche_age(
    data: TarificationTrancheAgeCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    amin, amax = data.age_min, data.age_max
    if amin is not None and amax is not None and amin > amax:
        raise HTTPException(status_code=400, detail="age_min > age_max")
    now = datetime.utcnow()
    row = TarificationTrancheAge(
        libelle=(data.libelle or "").strip() or None,
        age_min=data.age_min,
        age_max=data.age_max,
        coefficient=data.coefficient,
        ordre_priorite=data.ordre_priorite,
        est_actif=data.est_actif,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/tranches-age/{tranche_id}", response_model=TarificationTrancheAgeResponse)
def update_tranche_age(
    tranche_id: int,
    data: TarificationTrancheAgeUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    row = (
        db.query(TarificationTrancheAge)
        .filter(TarificationTrancheAge.id == tranche_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Tranche introuvable")
    payload = data.model_dump(exclude_unset=True)
    amin = payload.get("age_min", row.age_min)
    amax = payload.get("age_max", row.age_max)
    if amin is not None and amax is not None and amin > amax:
        raise HTTPException(status_code=400, detail="age_min > age_max")
    for k, v in payload.items():
        setattr(row, k, v)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row


@router.delete("/tranches-age/{tranche_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tranche_age(
    tranche_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    row = (
        db.query(TarificationTrancheAge)
        .filter(TarificationTrancheAge.id == tranche_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Tranche introuvable")
    db.delete(row)
    db.commit()
    return None


# ---------- Grille prix (zone × fenêtre durée), référence 18–69 ans ----------
@router.get("/grille", response_model=TarificationGrilleMatrixResponse)
def get_grille_matrix(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    zones = (
        db.query(TarificationZone)
        .order_by(TarificationZone.ordre_affichage.desc(), TarificationZone.nom)
        .all()
    )
    fenetres = (
        db.query(TarificationFenetreDuree)
        .order_by(
            TarificationFenetreDuree.ordre_priorite.desc(),
            TarificationFenetreDuree.duree_min_jours,
        )
        .all()
    )
    cellules = db.query(TarificationGrillePrix).all()
    return TarificationGrilleMatrixResponse(
        zones=[TarificationZoneResponse.model_validate(z) for z in zones],
        fenetres=[TarificationFenetreDureeResponse.model_validate(f) for f in fenetres],
        cellules=[
            TarificationGrillePrixCellResponse.model_validate(c) for c in cellules
        ],
    )


@router.put("/grille/cell", response_model=TarificationGrillePrixCellResponse)
def upsert_grille_cell(
    body: TarificationGrillePrixUpsert,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    z = db.query(TarificationZone).filter(TarificationZone.id == body.zone_id).first()
    if not z:
        raise HTTPException(status_code=400, detail="Zone introuvable")
    f = (
        db.query(TarificationFenetreDuree)
        .filter(TarificationFenetreDuree.id == body.fenetre_duree_id)
        .first()
    )
    if not f:
        raise HTTPException(status_code=400, detail="Fenêtre de durée introuvable")
    now = datetime.utcnow()
    row = (
        db.query(TarificationGrillePrix)
        .filter(
            TarificationGrillePrix.zone_id == body.zone_id,
            TarificationGrillePrix.fenetre_duree_id == body.fenetre_duree_id,
        )
        .first()
    )
    if row:
        row.prix = body.prix
        row.updated_at = now
    else:
        row = TarificationGrillePrix(
            zone_id=body.zone_id,
            fenetre_duree_id=body.fenetre_duree_id,
            prix=body.prix,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return TarificationGrillePrixCellResponse.model_validate(row)


@router.delete("/grille/cell", status_code=status.HTTP_204_NO_CONTENT)
def delete_grille_cell(
    zone_id: int = Query(..., ge=1),
    fenetre_duree_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    row = (
        db.query(TarificationGrillePrix)
        .filter(
            TarificationGrillePrix.zone_id == zone_id,
            TarificationGrillePrix.fenetre_duree_id == fenetre_duree_id,
        )
        .first()
    )
    if row:
        db.delete(row)
        db.commit()
    return None


# ---------- Grille finale (zone × durée × tranche) : tarif affiché au devis ----------
@router.get("/grille-finale", response_model=TarificationGrilleFinaleListResponse)
def list_grille_finale(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Grille globale uniquement (repli). Les grilles par produit : admin / produits / {id} / grille-finale."""
    cells = (
        db.query(TarificationGrilleFinale)
        .filter(TarificationGrilleFinale.produit_assurance_id.is_(None))
        .options(
            joinedload(TarificationGrilleFinale.zone),
            joinedload(TarificationGrilleFinale.fenetre),
            joinedload(TarificationGrilleFinale.tranche_age),
        )
        .all()
    )
    cells.sort(
        key=lambda c: (
            -(c.zone.ordre_affichage if c.zone else 0),
            (c.zone.nom or "").lower() if c.zone else "",
            -(c.fenetre.ordre_priorite if c.fenetre else 0),
            c.fenetre.duree_min_jours if c.fenetre else 0,
            -(c.tranche_age.ordre_priorite if c.tranche_age else 0),
            c.tranche_age_id,
        )
    )
    return TarificationGrilleFinaleListResponse(
        lignes=[_grille_finale_row_to_response(c) for c in cells],
    )


@router.put("/grille-finale/cell", response_model=TarificationGrilleFinaleRowResponse)
def upsert_grille_finale_cell(
    body: TarificationGrilleFinaleUpsert,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    z = db.query(TarificationZone).filter(TarificationZone.id == body.zone_id).first()
    if not z:
        raise HTTPException(status_code=400, detail="Zone introuvable")
    f = (
        db.query(TarificationFenetreDuree)
        .filter(TarificationFenetreDuree.id == body.fenetre_duree_id)
        .first()
    )
    if not f:
        raise HTTPException(status_code=400, detail="Fenêtre de durée introuvable")
    t = (
        db.query(TarificationTrancheAge)
        .filter(TarificationTrancheAge.id == body.tranche_age_id)
        .first()
    )
    if not t:
        raise HTTPException(status_code=400, detail="Tranche d'âge introuvable")
    coeff = body.coefficient_age if body.coefficient_age is not None else t.coefficient
    now = datetime.utcnow()
    row = (
        db.query(TarificationGrilleFinale)
        .filter(
            TarificationGrilleFinale.produit_assurance_id.is_(None),
            TarificationGrilleFinale.zone_id == body.zone_id,
            TarificationGrilleFinale.fenetre_duree_id == body.fenetre_duree_id,
            TarificationGrilleFinale.tranche_age_id == body.tranche_age_id,
        )
        .first()
    )
    if row:
        row.tarif_final = body.tarif_final
        row.coefficient_age = coeff
        row.updated_at = now
    else:
        row = TarificationGrilleFinale(
            produit_assurance_id=None,
            zone_id=body.zone_id,
            fenetre_duree_id=body.fenetre_duree_id,
            tranche_age_id=body.tranche_age_id,
            tarif_final=body.tarif_final,
            coefficient_age=coeff,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    row = (
        db.query(TarificationGrilleFinale)
        .options(
            joinedload(TarificationGrilleFinale.zone),
            joinedload(TarificationGrilleFinale.fenetre),
            joinedload(TarificationGrilleFinale.tranche_age),
        )
        .filter(TarificationGrilleFinale.id == row.id)
        .first()
    )
    return _grille_finale_row_to_response(row)


@router.delete("/grille-finale/cell", status_code=status.HTTP_204_NO_CONTENT)
def delete_grille_finale_cell(
    zone_id: int = Query(..., ge=1),
    fenetre_duree_id: int = Query(..., ge=1),
    tranche_age_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    row = (
        db.query(TarificationGrilleFinale)
        .filter(
            TarificationGrilleFinale.produit_assurance_id.is_(None),
            TarificationGrilleFinale.zone_id == zone_id,
            TarificationGrilleFinale.fenetre_duree_id == fenetre_duree_id,
            TarificationGrilleFinale.tranche_age_id == tranche_age_id,
        )
        .first()
    )
    if row:
        db.delete(row)
        db.commit()
    return None
