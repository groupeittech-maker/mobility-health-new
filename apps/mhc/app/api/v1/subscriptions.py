from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Optional
from decimal import Decimal
import json
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse, Response, RedirectResponse
from io import BytesIO
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload
from app.core.database import get_db
from app.core.enums import StatutSouscription, Role, StatutPaiement
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.souscription import Souscription
from app.models.produit_assurance import ProduitAssurance
from app.models.courtier import Courtier
from app.models.courtier_agent import CourtierAgent
from app.models.projet_voyage import ProjetVoyage
from app.models.attestation import Attestation
from app.models.paiement import Paiement
from app.models.finance_account import Account
from app.core.tarification_defaults import (
    DEFAULT_SURPRIME_70_75_PCT,
    DEFAULT_SURPRIME_76_80_PCT,
    DEFAULT_SURPRIME_81_89_PCT,
    DEFAULT_SURPRIME_MOINS_18_PCT,
    FRAIS_SERVICES_SUR_PRIME_PCT,
    ZONE_ROW_LABELS_FR,
)
from app.schemas.souscription import (
    SouscriptionResponse,
    SubscriptionQuotePricesRequest,
    SubscriptionQuotePricesResponse,
    SubscriptionQuotePriceItem,
    SurprimeAgeReferenceItem,
)
from app.schemas.ecard import ECardResponse
from app.schemas.subscription_decision import SubscriptionDecisionResult, VoyageurInfo
from app.services.attestation_service import (
    AttestationService,
    INLINE_BUCKET_NAME,
    INLINE_OBJECT_KEY,
)
from app.services.subscription_decision_service import SubscriptionDecisionEngine
from app.api.v1.attestations import (
    _get_ecard_public_base,
    _build_ecard_proxy_url,
    _is_internal_minio_url,
)
from app.services.finance_service import FinanceService
from app.services.prime_tarif_service import resolve_prime_tarif_detail
from pydantic import BaseModel
import re
import uuid
import logging
from app.models.projet_voyage_document import ProjetVoyageDocument
from app.services.card_service import CardService
from app.services.qrcode_service import QRCodeService
from app.services.project_document_storage import read_project_document_bytes

logger = logging.getLogger(__name__)

router = APIRouter()


def _quote_surprimes_age_reference() -> List[SurprimeAgeReferenceItem]:
    """% appliqués sur la prime grille (référence si champs produit vides)."""
    return [
        SurprimeAgeReferenceItem(
            tranche="Enfant de moins de 18 ans",
            pct=float(DEFAULT_SURPRIME_MOINS_18_PCT),
        ),
        SurprimeAgeReferenceItem(tranche="18 à 69 ans (référence)", pct=0.0),
        SurprimeAgeReferenceItem(
            tranche="70 à 75 ans",
            pct=float(DEFAULT_SURPRIME_70_75_PCT),
        ),
        SurprimeAgeReferenceItem(
            tranche="76 à 80 ans",
            pct=float(DEFAULT_SURPRIME_76_80_PCT),
        ),
        SurprimeAgeReferenceItem(
            tranche="81 à 89 ans et 90 ans et plus",
            pct=float(DEFAULT_SURPRIME_81_89_PCT),
        ),
    ]


def _age_from_birthdate(birthdate: Optional[date]) -> Optional[int]:
    """Calcule l'âge en années à partir de la date de naissance."""
    if not birthdate:
        return None
    today = date.today()
    return (today - birthdate).days // 365


def require_production_agent(current_user: User = Depends(get_current_user)) -> User:
    """Require the current user to be a production agent or admin"""
    if current_user.role not in {Role.PRODUCTION_AGENT, Role.ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Production agent or admin role required."
        )
    return current_user


# Rôles autorisés à souscrire pour un tiers (mêmes règles que POST /subscriptions/start).
from app.core.permissions import THIRD_PARTY_SUBSCRIPTION_ROLES, can_act_for_third_party


class SouscriptionStartRequest(BaseModel):
    """Schéma pour démarrer une souscription"""
    produit_assurance_id: int
    projet_voyage_id: Optional[int] = None
    date_debut: Optional[datetime] = None
    notes: Optional[str] = None
    user_id: Optional[int] = None  # ID de l'utilisateur pour qui on souscrit (pour souscription pour un tiers)
    # Caractéristiques pour tarif selon durée, zone et âge (sinon prix de base)
    destination_country_id: Optional[int] = None
    destination_country_name: Optional[str] = None
    residence_country_id: Optional[int] = None
    zone_code: Optional[str] = None
    duree_jours: Optional[int] = None
    age: Optional[int] = None  # Si absent, calculé depuis l'utilisateur cible (date_naissance)
    canal_distribution: Optional[str] = "assureur"  # assureur | courtier
    courtier_id: Optional[int] = None


class ClientSearchItem(BaseModel):
    id: int
    email: Optional[str] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    telephone: Optional[str] = None
    date_naissance: Optional[date] = None
    pays_residence: Optional[str] = None
    numero_passeport: Optional[str] = None
    sexe: Optional[str] = None


@router.get("/clients/search", response_model=List[ClientSearchItem])
async def search_subscription_clients(
    q: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Rechercher un assuré (compte client) pour créer une souscription à sa place.
    Réservé aux rôles autorisés à souscrire pour un tiers.
    """
    if current_user.role not in THIRD_PARTY_SUBSCRIPTION_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'avez pas les permissions pour rechercher des assurés.",
        )
    term = (q or "").strip()
    if len(term) < 3:
        return []
    pattern = f"%{term}%"
    users = (
        db.query(User)
        .filter(User.role == 'user')
        .filter(
            or_(
                User.email.ilike(pattern),
                User.full_name.ilike(pattern),
                User.username.ilike(pattern),
                User.telephone.ilike(pattern),
            )
        )
        .order_by(User.full_name)
        .limit(10)
        .all()
    )
    return users


@router.get("/clients/{client_id}", response_model=ClientSearchItem)
async def get_subscription_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Détail d'un assuré pour le parcours de souscription pour un tiers."""
    if current_user.role not in THIRD_PARTY_SUBSCRIPTION_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'avez pas les permissions pour consulter cet assuré.",
        )
    user = db.query(User).filter(User.id == client_id, User.role == 'user').first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assuré introuvable")
    return user


@router.post("/start", response_model=SouscriptionResponse, status_code=status.HTTP_201_CREATED)
async def start_subscription(
    subscription_data: SouscriptionStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Démarrer une nouvelle souscription en statut 'pending' (en_attente).
    Le prix est automatiquement calculé à partir du produit d'assurance.
    
    Si user_id est fourni, permet de souscrire pour un tiers (nécessite les permissions ADMIN ou PRODUCTION_AGENT).
    Sinon, la souscription est créée pour l'utilisateur connecté.
    """
    # Déterminer l'utilisateur pour qui on souscrit
    target_user_id = subscription_data.user_id if subscription_data.user_id else current_user.id
    
    # Si on essaie de souscrire pour un tiers, vérifier les permissions
    if subscription_data.user_id and subscription_data.user_id != current_user.id:
        # Vérifier que l'utilisateur actuel a les permissions pour souscrire pour un tiers
        if current_user.role not in THIRD_PARTY_SUBSCRIPTION_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'avez pas les permissions pour souscrire pour un tiers."
            )
        
        # Vérifier que l'utilisateur cible existe
        target_user = db.query(User).filter(User.id == subscription_data.user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Utilisateur avec l'ID {subscription_data.user_id} non trouvé"
            )
    
    canal_distribution = (subscription_data.canal_distribution or "assureur").strip().lower()
    if canal_distribution not in {"assureur", "courtier"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="canal_distribution invalide (assureur|courtier)",
        )
    selected_courtier_id: Optional[int] = None
    if canal_distribution == "courtier":
        courtier_id = subscription_data.courtier_id
        if not courtier_id:
            # Agent lié à un courtier (assistant souscription, agent production courtier) :
            # le courtier est déduit de l'affectation de l'agent.
            courtier_agent = db.query(CourtierAgent).filter(
                CourtierAgent.user_id == current_user.id,
                CourtierAgent.type_agent.in_(('production', 'souscription')),
            ).first()
            if courtier_agent:
                courtier_id = courtier_agent.courtier_id
        if not courtier_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="courtier_id requis pour le canal courtier",
            )
        courtier = db.query(Courtier).filter(Courtier.id == courtier_id).first()
        if not courtier:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Courtier introuvable")
        selected_courtier_id = courtier.id

    # Vérifier que le produit existe et est actif
    produit = db.query(ProduitAssurance).filter(
        ProduitAssurance.id == subscription_data.produit_assurance_id,
        ProduitAssurance.est_actif == True
    ).first()
    
    if not produit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produit d'assurance non trouvé ou inactif"
        )
    
    # Vérifier le projet de voyage si fourni
    projet = None
    if subscription_data.projet_voyage_id:
        projet = db.query(ProjetVoyage).filter(
            ProjetVoyage.id == subscription_data.projet_voyage_id
        ).first()
        
        if not projet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Projet de voyage non trouvé"
            )
        
        # Vérifier que le projet appartient à l'utilisateur cible (ou à l'utilisateur actuel si souscription pour soi)
        if projet.user_id != target_user_id:
            # Si l'utilisateur actuel a les permissions, on peut accepter même si le projet n'appartient pas à l'utilisateur cible
            if current_user.role not in {Role.ADMIN, Role.PRODUCTION_AGENT}:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Ce projet de voyage ne vous appartient pas"
                )
            # Si on a les permissions mais que le projet n'appartient pas à l'utilisateur cible, on avertit mais on continue
            logger.warning(
                f"Projet de voyage {projet.id} appartient à l'utilisateur {projet.user_id} "
                f"mais souscription créée pour l'utilisateur {target_user_id} par {current_user.id}"
            )
    
    # Âge : depuis la requête ou l'utilisateur cible (date_naissance)
    target_user = db.query(User).filter(User.id == target_user_id).first()
    age = subscription_data.age
    if age is None and target_user and getattr(target_user, "date_naissance", None):
        age = _age_from_birthdate(target_user.date_naissance)
    
    # Durée et zone : depuis la requête ou le projet
    duree_jours = subscription_data.duree_jours
    destination_country_id = subscription_data.destination_country_id
    zone_code = subscription_data.zone_code
    if projet:
        if duree_jours is None and projet.date_depart and projet.date_retour:
            delta = projet.date_retour - projet.date_depart
            duree_jours = max(1, delta.days)

    # Tarif selon parcours résidence → destination, durée et âge
    tarif_detail = resolve_prime_tarif_detail(
        db,
        product_id=produit.id,
        age=age,
        destination_country_id=destination_country_id,
        destination_country_name=subscription_data.destination_country_name,
        zone_code=zone_code,
        duree_jours=duree_jours,
        projet=projet,
        residence_country_id=subscription_data.residence_country_id,
        user_pays_residence=getattr(target_user, "pays_residence", None),
    )
    prix_applique = tarif_detail.prix
    
    # Déterminer la date de début
    date_debut = subscription_data.date_debut
    if not date_debut:
        if projet:
            date_debut = projet.date_depart
        else:
            date_debut = datetime.utcnow()
    
    # Déterminer la date de fin
    date_fin = None
    if produit.duree_validite_jours:
        date_fin = date_debut + timedelta(days=produit.duree_validite_jours)
    elif projet and projet.date_retour:
        date_fin = projet.date_retour
    
    # Générer un numéro de police MHC (nomenclature)
    from app.services.mhc_reference_service import allocate_police_number
    numero_souscription = allocate_police_number(db, country_name=projet.destination if projet else None)
    
    # Certains serveurs peuvent temporairement exécuter un modèle Souscription plus ancien
    # que l'API déployée. On filtre donc les kwargs optionnels pour éviter les 500.
    souscription_kwargs = {
        "user_id": target_user_id,  # Utiliser l'ID de l'utilisateur cible
        "produit_assurance_id": subscription_data.produit_assurance_id,
        "projet_voyage_id": subscription_data.projet_voyage_id,
        "numero_souscription": numero_souscription,
        "prix_applique": prix_applique,  # Prix calculé automatiquement
        "prime_assurance": tarif_detail.prime_assurance,
        "frais_services": tarif_detail.frais_services,
        "date_debut": date_debut,
        "date_fin": date_fin,
        "statut": StatutSouscription.EN_ATTENTE,  # Statut 'pending' (en_attente)
        "notes": subscription_data.notes,
    }
    if hasattr(Souscription, "cout_police"):
        souscription_kwargs["cout_police"] = tarif_detail.cout_police
    else:
        logger.warning("Souscription.cout_police absent sur le modèle chargé; valeur ignorée.")
    if hasattr(Souscription, "taxes"):
        souscription_kwargs["taxes"] = tarif_detail.taxes
    else:
        logger.warning("Souscription.taxes absent sur le modèle chargé; valeur ignorée.")
    if hasattr(Souscription, "taxes_total"):
        souscription_kwargs["taxes_total"] = tarif_detail.taxes_total
    if hasattr(Souscription, "canal_distribution"):
        souscription_kwargs["canal_distribution"] = canal_distribution
    else:
        logger.warning("Souscription.canal_distribution absent sur le modèle chargé; valeur ignorée.")
    if hasattr(Souscription, "courtier_id"):
        souscription_kwargs["courtier_id"] = selected_courtier_id
    else:
        logger.warning("Souscription.courtier_id absent sur le modèle chargé; valeur ignorée.")

    # Créer la souscription
    souscription = Souscription(**souscription_kwargs)
    
    db.add(souscription)
    db.commit()
    db.refresh(souscription)
    # Précharger les relations nécessaires pour la réponse
    souscription.produit_assurance = produit
    if projet:
        souscription.projet_voyage = projet

    # Produit voyage : la session eKYC est déclenchée automatiquement (le
    # CTA "Vérifier mon identité" la reprend côté mobile). Échec silencieux —
    # la souscription ne doit jamais dépendre de la disponibilité eKYC.
    if target_user is not None:
        from app.services import ekyc_service

        ekyc_service.auto_create_for_voyage(db, user=target_user, souscription=souscription)

    return souscription


@router.post("/quote-prices", response_model=SubscriptionQuotePricesResponse)
async def quote_subscription_prices(
    body: SubscriptionQuotePricesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Devis des primes pour plusieurs produits et un même projet de voyage,
    avec la même logique que POST /subscriptions/start (sans créer de souscription).
    Utilisé par l’app mobile à l’étape « choix du produit ».
    """
    projet = db.query(ProjetVoyage).filter(ProjetVoyage.id == body.projet_voyage_id).first()
    if not projet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projet de voyage introuvable",
        )
    if projet.user_id != current_user.id and current_user.role not in {
        Role.ADMIN,
        Role.PRODUCTION_AGENT,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce projet de voyage ne vous appartient pas",
        )

    target_user = current_user
    age = body.age
    if age is None and target_user and getattr(target_user, "date_naissance", None):
        age = _age_from_birthdate(target_user.date_naissance)

    duree_jours = body.duree_jours
    destination_country_id = body.destination_country_id
    zone_code = body.zone_code
    if projet:
        if duree_jours is None and projet.date_depart and projet.date_retour:
            delta = projet.date_retour - projet.date_depart
            duree_jours = max(1, delta.days)

    quotes: list[SubscriptionQuotePriceItem] = []
    seen: set[int] = set()
    for pid in body.produit_assurance_ids:
        if pid in seen:
            continue
        seen.add(pid)
        d = resolve_prime_tarif_detail(
            db,
            product_id=pid,
            age=age,
            destination_country_id=destination_country_id,
            destination_country_name=body.destination_country_name,
            zone_code=zone_code,
            duree_jours=duree_jours,
            projet=projet,
            residence_country_id=body.residence_country_id,
            user_pays_residence=getattr(target_user, "pays_residence", None),
        )
        zc = d.zone_geographique_code
        zl = ZONE_ROW_LABELS_FR.get(zc, zc) if zc else None
        taxe_list = []
        for t in d.taxes or []:
            taxe_list.append({
                "nom": t.get("nom", ""),
                "taux_pct": float(t.get("taux_pct", 0) or 0),
                "montant": float(t.get("montant", 0) or 0),
            })
        quotes.append(
            SubscriptionQuotePriceItem(
                produit_assurance_id=pid,
                prix_applique=float(d.prix),
                prime_assurance=float(d.prime_assurance) if d.prime_assurance is not None else None,
                cout_police=float(d.cout_police) if d.cout_police is not None else None,
                frais_services=float(d.frais_services) if d.frais_services is not None else None,
                taxes_total=float(d.taxes_total) if d.taxes_total is not None else None,
                taxes=taxe_list if taxe_list else None,
                montant_surprime=(
                    float(d.montant_surprime)
                    if getattr(d, "montant_surprime", None) is not None
                    else None
                ),
                pct_surprime_applique=(
                    float(d.pct_surprime_applique)
                    if getattr(d, "pct_surprime_applique", None) is not None
                    else None
                ),
                zone_geographique_code=zc,
                zone_libelle_fr=zl,
                tranche_duree_code=d.tranche_duree_code,
                duree_min_jours=d.duree_min_jours,
                duree_max_jours=d.duree_max_jours,
            )
        )
    return SubscriptionQuotePricesResponse(
        quotes=quotes,
        surprimes_age_reference=_quote_surprimes_age_reference(),
        frais_services_sur_prime_pct=float(FRAIS_SERVICES_SUR_PRIME_PCT),
    )


async def _get_subscriptions_impl(
    skip: int = 0,
    limit: int = 100,
    db: Session = None,
    current_user: User = None
):
    """Implémentation commune pour récupérer les souscriptions"""
    logger.info(f"Récupération des souscriptions pour l'utilisateur {current_user.id} (username: {current_user.username}, email: {current_user.email})")
    logger.info(f"Paramètres: skip={skip}, limit={limit}")
    
    # Compter le total de souscriptions pour cet utilisateur (sans limite)
    total_count = db.query(Souscription).filter(
        Souscription.user_id == current_user.id
    ).count()
    logger.info(f"Nombre total de souscriptions pour l'utilisateur {current_user.id}: {total_count}")
    
    souscriptions = (
        db.query(Souscription)
        .options(
            selectinload(Souscription.produit_assurance),
            selectinload(Souscription.projet_voyage),
        )
        .filter(Souscription.user_id == current_user.id)
        .order_by(Souscription.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    logger.info(f"Nombre de souscriptions retournées: {len(souscriptions)}")
    if souscriptions:
        logger.info(f"Statuts des souscriptions retournées: {[s.statut for s in souscriptions]}")
        logger.info(f"IDs des souscriptions: {[s.id for s in souscriptions]}")
    
    return souscriptions


@router.get("/", response_model=List[SouscriptionResponse])
async def get_subscriptions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir la liste des souscriptions de l'utilisateur (avec slash)"""
    return await _get_subscriptions_impl(skip=skip, limit=limit, db=db, current_user=current_user)


@router.get("", response_model=List[SouscriptionResponse], include_in_schema=False)
async def get_subscriptions_no_slash(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir la liste des souscriptions de l'utilisateur (sans slash - pour compatibilité mobile)"""
    return await _get_subscriptions_impl(skip=skip, limit=limit, db=db, current_user=current_user)


@router.get("/pending-resiliations", response_model=List[SouscriptionResponse])
async def get_pending_resiliations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_production_agent)
):
    """Obtenir la liste des souscriptions avec des demandes de résiliation en attente"""
    souscriptions = (
        db.query(Souscription)
        .options(
            selectinload(Souscription.produit_assurance),
            selectinload(Souscription.projet_voyage),
            selectinload(Souscription.user),
        )
        .filter(Souscription.demande_resiliation == "pending")
        .order_by(Souscription.demande_resiliation_date.desc())
        .all()
    )
    
    return souscriptions


@router.get("/{subscription_id}/user-photo")
async def get_subscription_user_photo(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir la photo d'identité de l'utilisateur depuis le questionnaire administratif de la souscription"""
    from app.models.questionnaire import Questionnaire
    
    # Vérifier que la souscription existe
    souscription = db.query(Souscription).filter(
        Souscription.id == subscription_id
    ).first()
    
    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée"
        )
    
    # Vérifier les permissions (utilisateur propriétaire ou rôles autorisés)
    allowed_roles = [
        Role.ADMIN,
        Role.SOS_OPERATOR,
        Role.DOCTOR,
        Role.MEDICAL_REVIEWER,
        Role.TECHNICAL_REVIEWER,
        Role.PRODUCTION_AGENT,
        Role.AGENT_SINISTRE_MH,
    ]
    if souscription.user_id != current_user.id and current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé"
        )
    
    # Récupérer le questionnaire administratif le plus récent
    questionnaire = (
        db.query(Questionnaire)
        .filter(
            Questionnaire.souscription_id == subscription_id,
            Questionnaire.type_questionnaire == "administratif",
        )
        .order_by(Questionnaire.version.desc())
        .first()
    )
    
    reponses = (questionnaire.reponses if questionnaire else None) or {}

    # Chercher la photo dans différents emplacements possibles
    personal = reponses.get("personal") or {}
    technical = reponses.get("technical") or {}

    photo_payload = (
        personal.get("photoIdentity") or
        personal.get("photo_identity") or
        technical.get("photoIdentity") or
        technical.get("photo_identity") or
        reponses.get("photoIdentity") or
        reponses.get("photo_identity") or
        reponses.get("identityPhoto") or
        reponses.get("identity_photo")
    )

    # Repli : la photo peut être stockée dans le questionnaire médical
    # (clés photo_medicale / photoMedicale / photo_identity, base64 data URL).
    if not photo_payload:
        medical = (
            db.query(Questionnaire)
            .filter(
                Questionnaire.souscription_id == subscription_id,
                Questionnaire.type_questionnaire == "medical",
            )
            .order_by(Questionnaire.version.desc())
            .first()
        )
        med_reponses = (medical.reponses if medical else None) or {}
        photo_payload = (
            med_reponses.get("photo_medicale") or
            med_reponses.get("photoMedicale") or
            med_reponses.get("photo_identity") or
            med_reponses.get("photoIdentity")
        )
    
    if not photo_payload:
        return {"photo_url": None}
    
    if not photo_payload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune photo d'identité",
        )

    # Extraire la photo (data URL base64, base64 brut ou URL)
    photo_url = None
    if isinstance(photo_payload, str):
        photo_url = photo_payload
    elif isinstance(photo_payload, dict):
        photo_url = (
            photo_payload.get("dataUrl") or
            photo_payload.get("url") or
            photo_payload.get("photo_url") or
            photo_payload.get("base64")
        )
        if photo_url and not str(photo_url).startswith(("data:", "http")):
            photo_url = f"data:image/jpeg;base64,{photo_url}"

    if not photo_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune photo d'identité",
        )

    # Le mobile attend les octets image bruts — décoder la data URL.
    if isinstance(photo_url, str) and photo_url.startswith("data:"):
        import base64
        header, _, b64 = photo_url.partition(",")
        media_type = "image/jpeg"
        if header.startswith("data:") and ";" in header:
            media_type = header[5:].split(";")[0] or "image/jpeg"
        try:
            content = base64.b64decode(b64)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Photo invalide",
            )
        return Response(content=content, media_type=media_type)

    # URL distante : laisser le client suivre la redirection.
    return RedirectResponse(photo_url)


@router.get("/{subscription_id}", response_model=SouscriptionResponse)
async def get_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir une souscription par ID"""
    query = db.query(Souscription).options(
        selectinload(Souscription.produit_assurance),
        selectinload(Souscription.projet_voyage),
    ).filter(Souscription.id == subscription_id)
    if not can_act_for_third_party(current_user.role):
        query = query.filter(Souscription.user_id == current_user.id)
    souscription = query.first()
    
    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée"
        )
    
    return souscription


@router.get("/{subscription_id}/ecard", response_model=ECardResponse)
async def get_subscription_ecard(
    request: Request,
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retourner la carte numérique associée à une souscription active."""
    souscription = (
        db.query(Souscription)
        .options(
            selectinload(Souscription.user),
            selectinload(Souscription.produit_assurance),
        )
        .filter(
            Souscription.id == subscription_id,
            Souscription.user_id == current_user.id,
        )
        .first()
    )

    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée",
        )

    attestation = (
        db.query(Attestation)
        .filter(
            Attestation.souscription_id == subscription_id,
            Attestation.type_attestation == "definitive",
            Attestation.est_valide == True,  # noqa: E712 - SQLAlchemy convention
        )
        .order_by(Attestation.created_at.desc())
        .first()
    )

    has_card = (
        attestation
        and (
            attestation.carte_numerique_url
            or (
                attestation.carte_numerique_path
                and attestation.carte_numerique_bucket
            )
        )
    )
    if not has_card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune carte numérique disponible pour cette souscription",
        )

    needs_refresh = (
        attestation.carte_numerique_path
        and attestation.carte_numerique_bucket
        and (
            not attestation.carte_numerique_expires_at
            or attestation.carte_numerique_expires_at
            <= datetime.utcnow() + timedelta(minutes=5)
        )
    )

    if needs_refresh:
        AttestationService.refresh_signed_url(
            db=db,
            attestation=attestation,
            expires=timedelta(hours=1),
            refresh_card=True,
        )
        db.refresh(attestation)

    # Extraire les informations du voyageur depuis le questionnaire administratif
    traveler_info = AttestationService._extract_traveler_info(db, souscription.id)
    
    # Utiliser les informations du voyageur si disponibles, sinon fallback sur l'utilisateur
    if traveler_info and traveler_info.get("fullName"):
        holder_name = traveler_info.get("fullName", "")
    else:
        user_obj = getattr(souscription, "user", None)
        if user_obj:
            holder_name = (
                user_obj.full_name
                or user_obj.username
                or user_obj.email
                or "Assuré(e)"
            )
        else:
            holder_name = "Assuré(e)"

    # Ne jamais renvoyer une URL minio:9000 (inaccessible depuis le navigateur).
    # Exception : carte « inline » (données base64, pas d'objet MinIO) — l'URL
    # data: est déjà auto-suffisante, ne pas la remplacer par le proxy.
    card_url = attestation.carte_numerique_url or ""
    is_inline_card = (
        attestation.carte_numerique_bucket == INLINE_BUCKET_NAME
        or attestation.carte_numerique_path == INLINE_OBJECT_KEY
        or card_url.startswith("data:")
    )
    if not is_inline_card and (
        (card_url and _is_internal_minio_url(card_url)) or (
            attestation.carte_numerique_path and attestation.carte_numerique_bucket and _get_ecard_public_base(request)
        )
    ):
        proxy = _build_ecard_proxy_url(attestation.id, request)
        if proxy:
            card_url = proxy
    elif not card_url and not is_inline_card and attestation.carte_numerique_path and attestation.carte_numerique_bucket:
        proxy = _build_ecard_proxy_url(attestation.id, request)
        if proxy:
            card_url = proxy

    return ECardResponse(
        subscription_id=souscription.id,
        numero_souscription=souscription.numero_souscription,
        holder_name=holder_name,
        card_url=card_url,
        card_expires_at=attestation.carte_numerique_expires_at,
        coverage_end_date=souscription.date_fin,
        generated_at=attestation.created_at,
    )


# ---------------------------------------------------------------------------
# E-cartes par membre assuré (adulte / tiers + enfants voyageurs)
# ---------------------------------------------------------------------------

def _member_name_from_mineur(m: Any) -> str:
    if not isinstance(m, dict):
        return str(m)
    nom = str(m.get("nom") or "").strip()
    prenom = str(m.get("prenom") or "").strip()
    return f"{prenom} {nom}".strip() or nom


def _subscription_members(db: Session, souscription: Souscription) -> List[Dict[str, Any]]:
    """Membres assurés d'une police.

    Index 0 = assuré principal : l'adulte souscripteur, ou le tiers pour une
    souscription « enfants uniquement » (marqueur « Pour un tiers » dans les
    notes). Les enfants voyageurs suivent, dans l'ordre du champ structuré
    `projet.mineurs`.
    """
    projet = None
    if souscription.projet_voyage_id:
        projet = db.query(ProjetVoyage).filter(
            ProjetVoyage.id == souscription.projet_voyage_id
        ).first()
    mineurs = list(getattr(projet, "mineurs", None) or [])
    notes = f"{getattr(projet, 'notes', '') or ''}\n{souscription.notes or ''}"
    is_tier = "pour un tiers" in notes.lower()

    members: List[Dict[str, Any]] = []
    if is_tier:
        if mineurs:
            for pos, m in enumerate(mineurs):
                members.append({
                    "index": pos,
                    "role": "child",
                    "name": _member_name_from_mineur(m),
                    "mineur": m if isinstance(m, dict) else None,
                    "mineur_pos": pos,
                    "principal": pos == 0,
                })
        else:
            # Ancien encodage : informations du tiers uniquement dans les notes.
            members.append({
                "index": 0, "role": "tier", "name": "",
                "mineur": None, "mineur_pos": None, "principal": True,
            })
    else:
        members.append({
            "index": 0, "role": "adult", "name": "",
            "mineur": None, "mineur_pos": None, "principal": True,
        })
        for pos, m in enumerate(mineurs):
            members.append({
                "index": pos + 1,
                "role": "child",
                "name": _member_name_from_mineur(m),
                "mineur": m if isinstance(m, dict) else None,
                "mineur_pos": pos,
                "principal": False,
            })
    return members


def _child_photo_bytes(
    db: Session, projet_id: Optional[int], mineur_pos: Optional[int]
) -> Optional[bytes]:
    """Photo portrait d'un enfant assuré : document `photo_enfant` taggé
    « [enfant:<pos>] » dans son libellé, sinon le n-ième document photo_enfant
    dans l'ordre d'envoi."""
    if not projet_id or mineur_pos is None:
        return None
    docs = (
        db.query(ProjetVoyageDocument)
        .filter(
            ProjetVoyageDocument.projet_voyage_id == projet_id,
            ProjetVoyageDocument.doc_type == "photo_enfant",
        )
        .order_by(ProjetVoyageDocument.uploaded_at, ProjetVoyageDocument.id)
        .all()
    )
    if not docs:
        return None
    target = None
    for d in docs:
        tag = re.search(r"\[enfant:(\d+)\]", d.display_name or "")
        if tag and int(tag.group(1)) == mineur_pos:
            target = d
            break
    if target is None and 0 <= mineur_pos < len(docs):
        target = docs[mineur_pos]
    if target is None:
        return None
    try:
        return read_project_document_bytes(target.bucket_name, target.object_name)
    except Exception as e:
        logger.warning(
            "Photo enfant illisible (doc %s, projet %s): %s",
            target.id, projet_id, e,
        )
        return None


def _get_owned_subscription_or_404(
    db: Session, subscription_id: int, current_user: User
) -> Souscription:
    souscription = (
        db.query(Souscription)
        .filter(
            Souscription.id == subscription_id,
            Souscription.user_id == current_user.id,
        )
        .first()
    )
    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée",
        )
    return souscription


def _generate_member_card_png(
    db: Session,
    souscription: Souscription,
    attestation: Attestation,
    member: Dict[str, Any],
) -> BytesIO:
    """Génère à la volée le PNG e-carte d'un enfant assuré (nom + photo de
    l'enfant — pas ceux du parent souscripteur)."""
    mineur = member.get("mineur") or {}
    traveler_info = {
        "fullName": member.get("name") or _member_name_from_mineur(mineur),
        "nom": mineur.get("nom"),
        "prenoms": mineur.get("prenom"),
        "dateNaissance": mineur.get("date_naissance"),
    }
    verification_url = AttestationService.build_verification_url(
        attestation.numero_attestation
    )
    qr_buffer = QRCodeService.generate_qr_image(verification_url)
    photo = _child_photo_bytes(
        db, souscription.projet_voyage_id, member.get("mineur_pos")
    )
    user_obj = db.query(User).filter(User.id == souscription.user_id).first()
    return CardService.generate_insurance_card(
        user_obj,
        souscription,
        attestation.numero_attestation,
        verification_url,
        photo_bytes=photo,
        qr_bytes=qr_buffer.getvalue() if qr_buffer else None,
        traveler_info=traveler_info,
        allow_missing_photo=True,
    )


@router.get("/{subscription_id}/ecard/members")
async def list_ecard_members(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste des membres assurés (une e-carte par membre) d'une souscription."""
    souscription = _get_owned_subscription_or_404(db, subscription_id, current_user)
    members = _subscription_members(db, souscription)
    principal_name = ""
    try:
        info = AttestationService._extract_traveler_info(db, souscription.id)
        principal_name = (info or {}).get("fullName") or ""
    except Exception:
        principal_name = ""
    if not principal_name:
        user_obj = getattr(souscription, "user", None) or db.query(User).filter(
            User.id == souscription.user_id
        ).first()
        principal_name = (
            getattr(user_obj, "full_name", None)
            or getattr(user_obj, "username", None)
            or getattr(user_obj, "email", None)
            or "Assuré(e)"
        )
    return {
        "subscription_id": souscription.id,
        "members": [
            {
                "index": m["index"],
                "role": m["role"],
                "name": m["name"] or principal_name,
            }
            for m in members
        ],
    }


@router.get("/{subscription_id}/ecard/member-photo")
async def get_ecard_member_photo(
    subscription_id: int,
    member: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Photo portrait d'un membre assuré (pour l'aperçu e-carte côté app)."""
    souscription = _get_owned_subscription_or_404(db, subscription_id, current_user)
    members = _subscription_members(db, souscription)
    target = next((m for m in members if m["index"] == member), None)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membre assuré introuvable",
        )
    photo = _child_photo_bytes(
        db, souscription.projet_voyage_id, target.get("mineur_pos")
    )
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune photo disponible pour ce membre",
        )
    return Response(content=photo, media_type="image/jpeg")


@router.get("/{subscription_id}/ecard/download")
async def download_subscription_ecard(
    subscription_id: int,
    member: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Télécharger directement la carte numérique depuis Minio (évite les problèmes d'URL signée).

    `member` (optionnel) = index du membre assuré retourné par `/ecard/members`.
    Sans paramètre (ou index du membre principal), la carte stockée est servie ;
    pour un enfant voyageur, sa carte est générée à la volée avec son nom et sa
    photo — l'e-carte du parent n'est jamais servie à la place.
    """
    souscription = (
        db.query(Souscription)
        .filter(
            Souscription.id == subscription_id,
            Souscription.user_id == current_user.id,
        )
        .first()
    )

    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée",
        )

    attestation = (
        db.query(Attestation)
        .filter(
            Attestation.souscription_id == subscription_id,
            Attestation.type_attestation == "definitive",
            Attestation.est_valide == True,  # noqa: E712 - SQLAlchemy convention
        )
        .order_by(Attestation.created_at.desc())
        .first()
    )

    if not attestation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune attestation définitive trouvée pour cette souscription",
        )

    # Carte d'un enfant voyageur : générée à la volée avec son nom et sa photo
    # (la carte stockée appartient au membre principal — jamais servie pour un
    # enfant, cf. retour test : la carte d'un mineur renvoyait celle de l'adulte).
    if member is not None:
        members = _subscription_members(db, souscription)
        target = next((m for m in members if m["index"] == member), None)
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Membre assuré introuvable",
            )
        if not target["principal"]:
            card_buffer = _generate_member_card_png(
                db, souscription, attestation, target
            )
            safe_name = re.sub(
                r"[^\w\-]+", "-", target["name"] or f"membre-{member}"
            ).strip("-")[:40] or "membre"
            return StreamingResponse(
                BytesIO(card_buffer.getvalue()),
                media_type="image/png",
                headers={
                    "Content-Disposition": (
                        f'attachment; filename="carte-'
                        f'{attestation.numero_attestation}-{safe_name}.png"'
                    )
                },
            )
        # Membre principal : carte stockée servie ci-dessous.

    if not attestation.carte_numerique_path or not attestation.carte_numerique_bucket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carte numérique non disponible (fichier non trouvé dans Minio)",
        )

    # Récupérer le fichier directement depuis Minio et le servir
    # (StreamingResponse / BytesIO sont déjà importés en tête de module —
    # un import local ici rendait le symbole « unbound » sur la branche membre).
    from app.services.minio_service import MinioService

    bucket_name = attestation.carte_numerique_bucket or MinioService.BUCKET_ATTESTATIONS

    try:
        # Vérifier que le fichier existe avant de le récupérer
        from app.core.minio_client import minio_client
        from minio.error import S3Error
        
        # Vérifier l'existence du fichier
        try:
            minio_client.stat_object(bucket_name, attestation.carte_numerique_path)
        except S3Error as stat_error:
            error_code = getattr(stat_error, 'code', 'Unknown')
            if error_code == 'NoSuchKey':
                import logging
                logger = logging.getLogger(__name__)
                logger.error(
                    f"Carte numérique non trouvée dans MinIO: {bucket_name}/{attestation.carte_numerique_path} "
                    f"(Souscription ID: {subscription_id}, Attestation ID: {attestation.id})"
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"La carte numérique n'existe pas dans le stockage. "
                           f"Chemin: {attestation.carte_numerique_path}"
                )
            else:
                raise
        
        # Récupérer le fichier depuis Minio
        response = minio_client.get_object(
            bucket_name,
            attestation.carte_numerique_path
        )
        
        # Lire le contenu du fichier
        file_data = response.read()
        response.close()
        response.release_conn()
        
        # Servir le fichier directement
        file_stream = BytesIO(file_data)
        return StreamingResponse(
            file_stream,
            media_type="image/png",
            headers={
                "Content-Disposition": f'attachment; filename="carte-{attestation.numero_attestation}.png"'
            }
        )
    except HTTPException:
        # Re-lancer les HTTPException telles quelles
        raise
    except S3Error as s3_error:
        # Erreur spécifique MinIO/S3
        import logging
        logger = logging.getLogger(__name__)
        
        # Extraire tous les détails de l'erreur
        error_details = MinioService.extract_error_details(s3_error)
        error_code = error_details.get('code') or 'Unknown'
        error_message = error_details.get('message') or str(s3_error)
        resource = error_details.get('resource')
        request_id = error_details.get('request_id')
        
        # Construire un message d'erreur détaillé
        error_info = f"Code: {error_code}, Message: {error_message}"
        if resource:
            error_info += f", Resource: {resource}"
        if request_id:
            error_info += f", RequestId: {request_id}"
        
        logger.error(
            f"Erreur MinIO lors de la récupération de la carte numérique "
            f"{bucket_name}/{attestation.carte_numerique_path}. {error_info}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Impossible d'accéder à la carte numérique. Erreur MinIO: {error_info}"
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(
            f"Erreur lors de la récupération de la carte numérique depuis Minio: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du téléchargement de la carte numérique: {str(e)}"
        )


class ResiliationRequest(BaseModel):
    """Schéma pour demander la résiliation d'une souscription"""
    notes: Optional[str] = None


class ResiliationDecisionRequest(BaseModel):
    """Schéma pour valider ou refuser une demande de résiliation"""
    approved: bool
    notes: Optional[str] = None


@router.post("/{subscription_id}/request-resiliation", response_model=SouscriptionResponse)
async def request_resiliation(
    subscription_id: int,
    request: ResiliationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Demander la résiliation d'une souscription"""
    souscription = (
        db.query(Souscription)
        .filter(
            Souscription.id == subscription_id,
            Souscription.user_id == current_user.id
        )
        .first()
    )
    
    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée"
        )
    
    # Vérifier que la souscription est active
    if souscription.statut != StatutSouscription.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seules les souscriptions actives peuvent être résiliées"
        )
    
    # Vérifier qu'il n'y a pas déjà une demande en cours
    if souscription.demande_resiliation == "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Une demande de résiliation est déjà en cours"
        )
    
    # Créer la demande de résiliation
    souscription.demande_resiliation = "pending"
    souscription.demande_resiliation_date = datetime.utcnow()
    souscription.demande_resiliation_notes = request.notes
    
    db.commit()
    db.refresh(souscription)
    
    return souscription


@router.post("/{subscription_id}/process-resiliation", response_model=SouscriptionResponse)
async def process_resiliation(
    subscription_id: int,
    decision: ResiliationDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_production_agent)
):
    """Valider ou refuser une demande de résiliation (agent de production)"""
    souscription = (
        db.query(Souscription)
        .options(
            selectinload(Souscription.produit_assurance),
            selectinload(Souscription.projet_voyage),
        )
        .filter(Souscription.id == subscription_id)
        .first()
    )
    
    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée"
        )
    
    # Vérifier qu'il y a une demande en cours
    if souscription.demande_resiliation != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucune demande de résiliation en cours"
        )
    
    # Traiter la demande
    souscription.demande_resiliation = "approved" if decision.approved else "rejected"
    souscription.demande_resiliation_par_agent = current_user.id
    souscription.demande_resiliation_date_traitement = datetime.utcnow()
    if decision.notes:
        souscription.demande_resiliation_notes = (
            (souscription.demande_resiliation_notes or "") + "\n\n" + decision.notes
        ).strip()
    
    # Si approuvé, marquer la souscription comme résiliée et créer le remboursement métier.
    if decision.approved:
        souscription.statut = StatutSouscription.RESILIEE
        souscription.date_fin = datetime.utcnow()
        
        # Résiliation:
        # - le courtier rembourse intégralement sa commission,
        # - l'assureur rembourse intégralement la prime,
        # - Mobility Health Care conserve 30 % de la prime.
        try:
            # Trouver le paiement associé à la souscription
            paiement = (
                db.query(Paiement)
                .filter(Paiement.souscription_id == souscription.id)
                .filter(Paiement.statut == StatutPaiement.VALIDE.name)
                .order_by(Paiement.created_at.desc())
                .first()
            )
            
            if paiement:
                montant_total = Decimal(str(souscription.prix_applique or Decimal("0.00")))
                prime = getattr(souscription, "prime_assurance", None)
                prime_base = (
                    Decimal(str(prime)).quantize(Decimal("0.01"))
                    if prime is not None
                    else montant_total
                )
                retention_mh = (prime_base * Decimal("0.30")).quantize(Decimal("0.01"))
                montant_remboursement = (montant_total - retention_mh).quantize(Decimal("0.01"))
                if montant_remboursement < Decimal("0.00"):
                    montant_remboursement = Decimal("0.00")
                
                # Trouver ou créer le compte financier du client
                account = (
                    db.query(Account)
                    .filter(Account.owner_id == souscription.user_id)
                    .filter(Account.account_type == "client")
                    .first()
                )
                
                if not account:
                    # Créer un compte client si il n'existe pas
                    account_number = f"CLIENT-{souscription.user_id}-{uuid.uuid4().hex[:8].upper()}"
                    account = Account(
                        account_number=account_number,
                        account_name=f"Compte client - {souscription.user_id}",
                        account_type="client",
                        balance=Decimal("0.00"),
                        currency="XAF",
                        is_active=True,
                        owner_id=souscription.user_id
                    )
                    db.add(account)
                    db.flush()  # Pour obtenir l'ID du compte
                    logger.info(f"Created client account {account.id} for user {souscription.user_id}")
                
                # Créer le remboursement via le service
                raison = (
                    f"Résiliation de la souscription {souscription.numero_souscription or souscription.id} "
                    f"(MH conserve 30 % de la prime: {retention_mh} XAF)"
                )
                if decision.notes:
                    raison += f" - {decision.notes}"
                
                FinanceService.process_refund(
                    db=db,
                    paiement_id=paiement.id,
                    account_id=account.id,
                    montant=montant_remboursement,
                    raison=raison,
                    processed_by=current_user.id
                )
                
                logger.info(
                    "Refund created for subscription %s: %s XAF (résiliation, retention MH %s XAF)",
                    souscription.id,
                    montant_remboursement,
                    retention_mh,
                )
            else:
                logger.warning(f"No valid payment found for subscription {souscription.id}, skipping refund")
        except Exception as e:
            logger.error(f"Error creating refund for subscription {souscription.id}: {e}", exc_info=True)
            # Ne pas bloquer la résiliation si le remboursement échoue
            # On continue quand même avec la résiliation

        try:
            AttestationService.issue_avenant_annulation(db, souscription)
        except Exception as avenant_error:
            logger.error(
                "Impossible de générer l'avenant d'annulation pour la souscription %s: %s",
                souscription.id,
                avenant_error,
                exc_info=True,
            )
    
    db.commit()
    db.refresh(souscription)
    
    return souscription


@router.get("/{subscription_id}/avenant-annulation/download")
async def download_avenant_annulation(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Télécharge l'avenant d'annulation (document distinct de l'attestation)."""
    souscription = (
        db.query(Souscription)
        .filter(Souscription.id == subscription_id)
        .first()
    )
    if not souscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Souscription non trouvée")
    if souscription.user_id != current_user.id and current_user.role not in {
        Role.ADMIN,
        Role.PRODUCTION_AGENT,
    }:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")

    attestation = (
        db.query(Attestation)
        .filter(Attestation.souscription_id == subscription_id)
        .order_by(Attestation.created_at.desc())
        .first()
    )
    payload = {}
    if attestation and attestation.notes:
        try:
            payload = json.loads(attestation.notes).get("avenant_annulation") or {}
        except Exception:
            payload = {}
    if payload.get("inline"):
        import base64
        raw = payload["inline"].split(",", 1)[-1]
        data = base64.b64decode(raw)
        return StreamingResponse(
            BytesIO(data),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="avenant-{payload.get("numero", subscription_id)}.pdf"'},
        )
    if payload.get("path") and payload.get("bucket"):
        from app.core.minio_client import minio_client
        obj = minio_client.get_object(payload["bucket"], payload["path"])
        data = obj.read()
        return StreamingResponse(
            BytesIO(data),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="avenant-{payload.get("numero", subscription_id)}.pdf"'},
        )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avenant d'annulation introuvable")


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Supprimer une souscription résiliée, ou un brouillon / « à payer »
    (liste « En attente » de MyMHC)."""
    from app.services.subscription_cleanup import DELETABLE_STATUSES, deletion_blocker

    souscription = (
        db.query(Souscription)
        .filter(
            Souscription.id == subscription_id,
            Souscription.user_id == current_user.id
        )
        .first()
    )
    
    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée"
        )
    
    if souscription.statut in DELETABLE_STATUSES:
        blocker = deletion_blocker(db, souscription)
        if blocker:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=blocker)
    elif souscription.statut != StatutSouscription.RESILIEE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seules les souscriptions résiliées, brouillons ou à payer peuvent être supprimées"
        )
    
    # Supprimer la souscription (les attestations seront supprimées en cascade)
    db.delete(souscription)
    db.commit()

    return None


@router.post(
    "/{subscription_id}/evaluate",
    response_model=SubscriptionDecisionResult,
    status_code=status.HTTP_200_OK,
)
async def evaluate_subscription(
    subscription_id: int,
    voyageur: Optional[VoyageurInfo] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Évalue automatiquement une souscription juste après la soumission du dossier.

    Décisions possibles :
    - approve : souscription approuvée, en attente de paiement
    - reject  : souscription refusée
    - review  : dossier à valider par le pipeline médical / technique / production
    """
    query = (
        db.query(Souscription)
        .options(
            selectinload(Souscription.user),
            selectinload(Souscription.produit_assurance),
            selectinload(Souscription.projet_voyage),
        )
        .filter(Souscription.id == subscription_id)
    )
    if not can_act_for_third_party(current_user.role):
        query = query.filter(Souscription.user_id == current_user.id)
    souscription = query.first()

    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Souscription non trouvée",
        )

    voyageur_date = None
    if voyageur and voyageur.voyageur_date_naissance:
        try:
            voyageur_date = datetime.fromisoformat(voyageur.voyageur_date_naissance).date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Format de voyageur_date_naissance invalide (attendu YYYY-MM-DD)",
            )

    result = SubscriptionDecisionEngine.evaluate(
        db,
        souscription,
        voyageur_age=getattr(voyageur, "voyageur_age", None),
        voyageur_date_naissance=voyageur_date,
    )
    db.commit()
    db.refresh(souscription)

    return SubscriptionDecisionResult(
        souscription_id=souscription.id,
        numero_souscription=souscription.numero_souscription,
        decision=result.decision,
        primary_step=result.primary_step,
        review_steps=result.review_steps,
        reasons=result.reasons,
        risk_score=result.risk_score,
        statut=souscription.statut.value,
    )

class InfoResponseBody(BaseModel):
    reponse: str


@router.post("/{subscription_id}/info-response", response_model=SouscriptionResponse)
async def respond_to_info_request(
    subscription_id: int,
    body: InfoResponseBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Réponse de l'assuré à une demande d'informations complémentaires (§4.2)."""
    from app.services.subscription_lifecycle import respond_info

    souscription = (
        db.query(Souscription)
        .filter(Souscription.id == subscription_id, Souscription.user_id == current_user.id)
        .first()
    )
    if not souscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Souscription non trouvée")
    return respond_info(db, souscription, body.reponse)
