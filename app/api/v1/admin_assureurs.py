from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from app.services.minio_service import MinioService

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.core.enums import Role
from app.models.assureur import Assureur
from app.models.assureur_agent import AssureurAgent
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.assureur import AssureurCreate, AssureurUpdate, AssureurResponse

router = APIRouter()


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin role required.",
        )
    return current_user


def _get_assureur_or_404(db: Session, assureur_id: int) -> Assureur:
    assureur = db.query(Assureur).filter(Assureur.id == assureur_id).first()
    if not assureur:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assureur introuvable",
        )
    return assureur


def _build_assureur_response(db: Session, assureur: Assureur) -> dict:
    """Construit le dict de réponse AssureurResponse pour éviter la sérialisation Pydantic des ORM agents."""
    agent_comptable_data = None
    if assureur.agent_comptable_id:
        try:
            agent_comptable = db.query(User).filter(User.id == assureur.agent_comptable_id).first()
            if agent_comptable:
                role_value = agent_comptable.role.value if hasattr(agent_comptable.role, 'value') else str(agent_comptable.role)
                agent_comptable_data = {
                    "id": agent_comptable.id,
                    "email": agent_comptable.email,
                    "username": agent_comptable.username,
                    "full_name": agent_comptable.full_name,
                    "role": role_value,
                    "is_active": agent_comptable.is_active,
                }
        except Exception:
            pass
    agents_data = []
    try:
        if hasattr(assureur, 'agents') and assureur.agents:
            for agent in assureur.agents:
                try:
                    role_value = agent.user.role.value if hasattr(agent.user.role, 'value') else str(agent.user.role)
                    agents_data.append({
                        "id": agent.user.id,
                        "email": agent.user.email,
                        "username": agent.user.username,
                        "full_name": agent.user.full_name,
                        "role": role_value,
                        "is_active": agent.user.is_active,
                        "type_agent": agent.type_agent,
                    })
                except Exception:
                    continue
    except Exception:
        pass
    return {
        "id": assureur.id,
        "nom": assureur.nom,
        "pays": assureur.pays or "",
        "logo_url": assureur.logo_url,
        "adresse": assureur.adresse,
        "telephone": assureur.telephone,
        "agent_comptable_id": assureur.agent_comptable_id,
        "agent_comptable": agent_comptable_data,
        "agents": agents_data if agents_data else None,
        "created_at": assureur.created_at,
        "updated_at": assureur.updated_at,
    }


def _ensure_agent_comptable(db: Session, agent_id: Optional[int]) -> Optional[User]:
    if agent_id is None:
        return None
    agent = db.query(User).filter(User.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent comptable introuvable",
        )
    if agent.role != Role.AGENT_COMPTABLE_ASSUREUR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le compte sélectionné n'est pas un agent comptable assureur",
        )
    if not agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="L'agent comptable sélectionné est inactif",
        )
    return agent


def _validate_agent_role(agent: User, expected_role: Role) -> None:
    """Valide qu'un agent a le bon rôle"""
    if agent.role != expected_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le compte sélectionné n'est pas un {expected_role.value}",
        )
    if not agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="L'agent sélectionné est inactif",
        )


def _check_agent_not_assigned(db: Session, agent_id: int, exclude_assureur_id: Optional[int] = None) -> None:
    """Vérifie qu'un agent n'est pas déjà affecté à un autre assureur"""
    query = db.query(AssureurAgent).filter(AssureurAgent.user_id == agent_id)
    if exclude_assureur_id:
        query = query.filter(AssureurAgent.assureur_id != exclude_assureur_id)
    existing = query.first()
    if existing:
        assureur = db.query(Assureur).filter(Assureur.id == existing.assureur_id).first()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cet agent est déjà affecté à l'assureur '{assureur.nom if assureur else 'inconnu'}'. Un agent ne peut être affecté qu'à un seul assureur.",
        )


def _manage_assureur_agents(
    db: Session,
    assureur_id: int,
    agents_comptables_ids: Optional[List[int]] = None,
    agents_production_ids: Optional[List[int]] = None,
    agents_sinistre_ids: Optional[List[int]] = None,
) -> None:
    """Gère les agents d'un assureur (supprime les anciens et ajoute les nouveaux)"""
    # Vérifier si la table existe, sinon on ne fait rien (migration pas encore appliquée)
    try:
        # Test si la table existe
        db.query(AssureurAgent).limit(1).all()
    except Exception:
        # Table n'existe pas encore, on ignore cette fonctionnalité
        return
    
    # Récupérer les IDs des agents actuellement affectés à cet assureur
    try:
        current_agent_ids = {
            row[0] for row in db.query(AssureurAgent.user_id)
            .filter(AssureurAgent.assureur_id == assureur_id)
            .all()
        }
    except Exception:
        current_agent_ids = set()
    
    # Construire la liste complète des nouveaux agents
    all_new_agent_ids = set()
    if agents_comptables_ids:
        all_new_agent_ids.update(agents_comptables_ids)
    if agents_production_ids:
        all_new_agent_ids.update(agents_production_ids)
    if agents_sinistre_ids:
        all_new_agent_ids.update(agents_sinistre_ids)
    
    # Vérifier tous les nouveaux agents AVANT de supprimer
    all_agent_ids_to_check = list(all_new_agent_ids)
    for agent_id in all_agent_ids_to_check:
        # Si l'agent est déjà affecté à cet assureur, on peut le garder
        if agent_id in current_agent_ids:
            continue
        # Sinon, vérifier qu'il n'est pas affecté à un autre assureur
        _check_agent_not_assigned(db, agent_id, exclude_assureur_id=assureur_id)
    
    # Valider les rôles de tous les agents
    if agents_comptables_ids:
        for agent_id in agents_comptables_ids:
            agent = db.query(User).filter(User.id == agent_id).first()
            if agent:
                _validate_agent_role(agent, Role.AGENT_COMPTABLE_ASSUREUR)
    
    if agents_production_ids:
        for agent_id in agents_production_ids:
            agent = db.query(User).filter(User.id == agent_id).first()
            if agent:
                _validate_agent_role(agent, Role.PRODUCTION_AGENT)
    
    if agents_sinistre_ids:
        for agent_id in agents_sinistre_ids:
            agent = db.query(User).filter(User.id == agent_id).first()
            if agent:
                _validate_agent_role(agent, Role.AGENT_SINISTRE_ASSUREUR)
    
    # Maintenant, supprimer tous les agents existants pour cet assureur
    try:
        db.query(AssureurAgent).filter(AssureurAgent.assureur_id == assureur_id).delete()
    except Exception:
        # Si erreur, on continue quand même
        pass
    
    # Ajouter les nouveaux agents comptables
    if agents_comptables_ids:
        for agent_id in agents_comptables_ids:
            agent = db.query(User).filter(User.id == agent_id).first()
            if not agent:
                continue
            assureur_agent = AssureurAgent(
                assureur_id=assureur_id,
                user_id=agent_id,
                type_agent='comptable'
            )
            db.add(assureur_agent)
    
    # Ajouter les nouveaux agents production
    if agents_production_ids:
        for agent_id in agents_production_ids:
            agent = db.query(User).filter(User.id == agent_id).first()
            if not agent:
                continue
            assureur_agent = AssureurAgent(
                assureur_id=assureur_id,
                user_id=agent_id,
                type_agent='production'
            )
            db.add(assureur_agent)
    
    # Ajouter les nouveaux agents sinistre
    if agents_sinistre_ids:
        for agent_id in agents_sinistre_ids:
            agent = db.query(User).filter(User.id == agent_id).first()
            if not agent:
                continue
            assureur_agent = AssureurAgent(
                assureur_id=assureur_id,
                user_id=agent_id,
                type_agent='sinistre'
            )
            db.add(assureur_agent)


@router.get("", response_model=List[AssureurResponse])
async def list_assureurs(
    search: Optional[str] = Query(None, description="Filtrer par nom ou pays"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    import logging
    logger = logging.getLogger(__name__)
    
    # Réinitialiser la session en cas de transaction invalide
    try:
        from sqlalchemy import text
        # Tester la connexion et réinitialiser si nécessaire
        db.execute(text("SELECT 1"))
    except Exception:
        # Si la transaction est invalide, faire un rollback
        try:
            db.rollback()
        except Exception:
            pass
    
    try:
        query = db.query(Assureur)
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Assureur.nom.ilike(pattern),
                    Assureur.pays.ilike(pattern),
                )
            )
        
        # Essayer de charger les agents, mais gérer le cas où la table n'existe pas encore
        try:
            assureurs = query.options(selectinload(Assureur.agents)).order_by(Assureur.nom.asc()).all()
        except Exception as e:
            # Si la table assureur_agents n'existe pas encore, charger sans les agents
            logger.warning(f"Erreur lors du chargement de la relation agents: {e}")
            # Rollback en cas d'erreur et réessayer
            try:
                db.rollback()
            except Exception:
                pass
            assureurs = query.order_by(Assureur.nom.asc()).all()
        
        # Transformer les agents en format de réponse
        logger.info(f"Récupération de {len(assureurs)} assureurs")
        result = []
        for assureur in assureurs:
            # Charger agent_comptable si disponible
            agent_comptable_data = None
            if assureur.agent_comptable_id:
                try:
                    agent_comptable = db.query(User).filter(User.id == assureur.agent_comptable_id).first()
                    if agent_comptable:
                        role_value = agent_comptable.role.value if hasattr(agent_comptable.role, 'value') else str(agent_comptable.role)
                        agent_comptable_data = {
                            "id": agent_comptable.id,
                            "email": agent_comptable.email,
                            "username": agent_comptable.username,
                            "full_name": agent_comptable.full_name,
                            "role": role_value,
                            "is_active": agent_comptable.is_active,
                        }
                except Exception:
                    pass
            
            # Charger les agents de la nouvelle table si disponible
            agents_data = []
            try:
                if hasattr(assureur, 'agents') and assureur.agents:
                    agents_data = []
                    for agent in assureur.agents:
                        try:
                            role_value = agent.user.role.value if hasattr(agent.user.role, 'value') else str(agent.user.role)
                            agents_data.append({
                                "id": agent.user.id,
                                "email": agent.user.email,
                                "username": agent.user.username,
                                "full_name": agent.user.full_name,
                                "role": role_value,
                                "is_active": agent.user.is_active,
                                "type_agent": agent.type_agent,
                            })
                        except Exception as e:
                            # Ignorer les agents avec des erreurs de chargement
                            logger.warning(f"Erreur lors du chargement de l'agent {agent.user_id}: {e}")
                            continue
            except Exception:
                pass
            
            try:
                # Utiliser le schéma Pydantic pour la sérialisation
                from app.schemas.assureur import AssureurResponse, AgentComptableSummary, AgentSummary
                
                # Construire les données pour le schéma
                assureur_data = {
                    "id": assureur.id,
                    "nom": assureur.nom,
                    "pays": assureur.pays or "",
                    "logo_url": assureur.logo_url,
                    "adresse": assureur.adresse,
                    "telephone": assureur.telephone,
                    "agent_comptable_id": assureur.agent_comptable_id,
                    "created_at": assureur.created_at,
                    "updated_at": assureur.updated_at,
                }
                
                # Ajouter agent_comptable si disponible
                if agent_comptable_data:
                    assureur_data["agent_comptable"] = AgentComptableSummary(**agent_comptable_data)
                
                # Ajouter agents si disponibles
                if agents_data:
                    assureur_data["agents"] = [AgentSummary(**agent) for agent in agents_data]
                
                assureur_response = AssureurResponse(**assureur_data)
                result.append(assureur_response)
            except Exception as e:
                logger.error(f"Erreur lors de la sérialisation de l'assureur {assureur.id}: {e}", exc_info=True)
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                # En cas d'erreur, créer un assureur minimal
                try:
                    assureur_data = {
                        "id": assureur.id,
                        "nom": assureur.nom,
                        "pays": assureur.pays or "",
                        "logo_url": None,
                        "adresse": None,
                        "telephone": None,
                        "agent_comptable_id": assureur.agent_comptable_id,
                        "created_at": assureur.created_at,
                        "updated_at": assureur.updated_at,
                    }
                    assureur_response = AssureurResponse(**assureur_data)
                    result.append(assureur_response)
                except Exception as fallback_error:
                    logger.error(f"Impossible de sérialiser l'assureur {assureur.id}: {fallback_error}", exc_info=True)
                    logger.error(f"Traceback fallback: {traceback.format_exc()}")
        
        logger.info(f"Retour de {len(result)} assureurs sérialisés")
        return result
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des assureurs: {e}", exc_info=True)
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Rollback en cas d'erreur de transaction
        try:
            db.rollback()
        except Exception as rollback_error:
            logger.warning(f"Erreur lors du rollback: {rollback_error}")
            # Si le rollback échoue, fermer et rouvrir la session
            try:
                db.close()
            except Exception:
                pass
        
        # Extraire le message d'erreur principal
        error_msg = str(e)
        if "InFailedSqlTransaction" in error_msg:
            error_msg = "Erreur de transaction SQL. Veuillez réessayer."
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des assureurs: {error_msg}"
        )


@router.post("", response_model=AssureurResponse, status_code=status.HTTP_201_CREATED)
async def create_assureur(
    payload: AssureurCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    nom_normalized = payload.nom.strip()
    existing = (
        db.query(Assureur)
        .filter(func.lower(Assureur.nom) == nom_normalized.lower())
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un assureur avec ce nom existe déjà.",
        )

    agent = _ensure_agent_comptable(db, payload.agent_comptable_id)

    assureur = Assureur(
        nom=nom_normalized,
        pays=payload.pays.strip(),
        logo_url=payload.logo_url,
        adresse=payload.adresse,
        telephone=payload.telephone,
        agent_comptable_id=agent.id if agent else None,
    )

    db.add(assureur)
    db.commit()
    db.refresh(assureur)
    
    # Gérer les nouveaux agents (comptables, production, sinistre)
    _manage_assureur_agents(
        db,
        assureur.id,
        agents_comptables_ids=payload.agents_comptables_ids,
        agents_production_ids=payload.agents_production_ids,
        agents_sinistre_ids=payload.agents_sinistre_ids,
    )
    db.commit()
    db.refresh(assureur)

    role_value = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    audit_log = AuditLog(
        timestamp=datetime.utcnow(),
        method="POST",
        path="/api/v1/admin/assureurs",
        user_id=current_user.id,
        user_role=role_value,
        status_code=status.HTTP_201_CREATED,
        request_body=f"Assureur créé: {assureur.nom}",
    )
    db.add(audit_log)
    db.commit()

    db.refresh(assureur)
    try:
        assureur = db.query(Assureur).options(selectinload(Assureur.agents)).filter(Assureur.id == assureur.id).first()
    except Exception:
        pass
    return _build_assureur_response(db, assureur)


@router.get("/{assureur_id}", response_model=AssureurResponse)
async def get_assureur(
    assureur_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    # Essayer de charger avec les agents, mais gérer le cas où la table n'existe pas
    try:
        assureur = db.query(Assureur).options(selectinload(Assureur.agents)).filter(Assureur.id == assureur_id).first()
    except Exception:
        assureur = db.query(Assureur).filter(Assureur.id == assureur_id).first()
    
    if not assureur:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assureur introuvable",
        )
    
    return _build_assureur_response(db, assureur)


@router.put("/{assureur_id}", response_model=AssureurResponse)
async def update_assureur(
    assureur_id: int,
    payload: AssureurUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    assureur = _get_assureur_or_404(db, assureur_id)

    if payload.nom and payload.nom.strip().lower() != assureur.nom.lower():
        duplicate = (
            db.query(Assureur)
            .filter(
                func.lower(Assureur.nom) == payload.nom.strip().lower(),
                Assureur.id != assureur_id,
            )
            .first()
        )
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un assureur avec ce nom existe déjà.",
            )

    update_data = payload.model_dump(exclude_unset=True)
    
    # Gérer l'ancien champ agent_comptable_id (rétrocompatibilité)
    agent_field_provided = "agent_comptable_id" in update_data
    agent_to_assign = None
    if agent_field_provided:
        agent_id_value = update_data.pop("agent_comptable_id")
        agent_to_assign = (
            _ensure_agent_comptable(db, agent_id_value) if agent_id_value is not None else None
        )
    
    # Extraire les listes d'agents
    # Vérifier si les champs sont présents dans update_data (fournis explicitement, même si None)
    agents_comptables_provided = "agents_comptables_ids" in update_data
    agents_production_provided = "agents_production_ids" in update_data
    agents_sinistre_provided = "agents_sinistre_ids" in update_data
    
    agents_comptables_ids = update_data.pop("agents_comptables_ids", None) if agents_comptables_provided else None
    agents_production_ids = update_data.pop("agents_production_ids", None) if agents_production_provided else None
    agents_sinistre_ids = update_data.pop("agents_sinistre_ids", None) if agents_sinistre_provided else None
    
    # Mettre à jour les autres champs
    for field, value in update_data.items():
        if field == "nom" and value:
            setattr(assureur, field, value.strip())
        elif field == "pays" and value:
            setattr(assureur, field, value.strip())
        else:
            setattr(assureur, field, value)

    if agent_field_provided:
        assureur.agent_comptable_id = agent_to_assign.id if agent_to_assign else None

    # Gérer les nouveaux agents (comptables, production, sinistre)
    # Si au moins une liste est fournie (même None ou vide), on met à jour tous les agents
    # None signifie "supprimer tous les agents de ce type", [] signifie "aucun agent"
    agents_provided = agents_comptables_provided or agents_production_provided or agents_sinistre_provided
    if agents_provided:
        # Convertir None en liste vide pour supprimer tous les agents
        _manage_assureur_agents(
            db,
            assureur.id,
            agents_comptables_ids=agents_comptables_ids if agents_comptables_ids is not None else [],
            agents_production_ids=agents_production_ids if agents_production_ids is not None else [],
            agents_sinistre_ids=agents_sinistre_ids if agents_sinistre_ids is not None else [],
        )

    db.commit()
    db.refresh(assureur)

    role_value = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    audit_log = AuditLog(
        timestamp=datetime.utcnow(),
        method="PUT",
        path=f"/api/v1/admin/assureurs/{assureur_id}",
        user_id=current_user.id,
        user_role=role_value,
        status_code=status.HTTP_200_OK,
        request_body=f"Assureur mis à jour: {assureur.nom}",
    )
    db.add(audit_log)
    db.commit()

    db.refresh(assureur)
    try:
        assureur = db.query(Assureur).options(selectinload(Assureur.agents)).filter(Assureur.id == assureur.id).first()
    except Exception:
        pass
    return _build_assureur_response(db, assureur)


ALLOWED_LOGO_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
ALLOWED_LOGO_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}


@router.post("/{assureur_id}/logo", status_code=status.HTTP_200_OK)
async def upload_assureur_logo(
    assureur_id: int,
    file: UploadFile = File(..., description="Fichier image du logo (PNG, JPG, GIF, WebP)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Upload le logo d'un assureur (fichier image). Remplace l'URL par la référence au fichier stocké."""
    assureur = _get_assureur_or_404(db, assureur_id)
    if not file.content_type or file.content_type not in ALLOWED_LOGO_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Type de fichier non autorisé. Utilisez: {', '.join(ALLOWED_LOGO_CONTENT_TYPES)}",
        )
    ext = (file.filename or "").split(".")[-1].lower() if file.filename else "png"
    if ext not in ALLOWED_LOGO_EXTENSIONS:
        ext = "png"
    content_type = file.content_type
    try:
        body = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Impossible de lire le fichier: {e}",
        )
    if not body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier est vide.",
        )
    try:
        logo_key = MinioService.upload_assureur_logo(assureur_id, body, content_type, ext)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du stockage du logo: {e}",
        )
    assureur.logo_url = logo_key
    db.commit()
    db.refresh(assureur)
    return {"logo_url": logo_key, "message": "Logo enregistré."}


@router.get("/agents/available", response_model=List[dict])
async def get_available_agents(
    role: str = Query(..., description="Rôle de l'agent à récupérer (peut être un string ou un enum)"),
    exclude_assureur_id: Optional[int] = Query(None, description="ID de l'assureur à exclure (pour permettre la modification)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Récupère les agents disponibles pour un rôle donné.
    Exclut les agents déjà affectés à un autre assureur.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Mapper les rôles string aux enums
        role_mapping = {
            "agent_comptable_assureur": Role.AGENT_COMPTABLE_ASSUREUR,
            "production_agent": Role.PRODUCTION_AGENT,
            "agent_sinistre_assureur": Role.AGENT_SINISTRE_ASSUREUR,
        }
        
        # Convertir le rôle string en enum si nécessaire
        if isinstance(role, str):
            role_enum = role_mapping.get(role)
            if not role_enum:
                # Essayer de convertir directement
                try:
                    role_enum = Role(role)
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Rôle invalide: {role}. Rôles valides: {list(role_mapping.keys())}"
                    )
        else:
            role_enum = role
        
        # Récupérer tous les agents avec ce rôle
        agents = db.query(User).filter(
            User.role == role_enum,
            User.is_active == True
        ).all()
        
        # Récupérer les IDs des agents déjà affectés (sauf à l'assureur exclu)
        assigned_agent_ids = set()
        try:
            query = db.query(AssureurAgent.user_id)
            if exclude_assureur_id:
                query = query.filter(AssureurAgent.assureur_id != exclude_assureur_id)
            assigned_agent_ids = {row[0] for row in query.all()}
        except Exception as e:
            # Si la table assureur_agents n'existe pas encore, aucun agent n'est assigné
            logger.warning(f"Table assureur_agents non disponible: {e}. Aucun agent n'est considéré comme assigné.")
            assigned_agent_ids = set()
        
        # Filtrer les agents disponibles
        available_agents = [
            {
                "id": agent.id,
                "email": agent.email,
                "username": agent.username,
                "full_name": agent.full_name,
                "role": agent.role.value if hasattr(agent.role, 'value') else str(agent.role),
                "is_active": agent.is_active,
                "is_assigned": agent.id in assigned_agent_ids,
            }
            for agent in agents
            if agent.id not in assigned_agent_ids
        ]
        
        return available_agents
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des agents disponibles: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des agents disponibles: {str(e)}"
        )


