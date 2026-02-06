from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func
from app.core.database import get_db, SessionLocal
from app.core.enums import Role, StatutWorkflowSinistre
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.alerte import Alerte
from app.models.sinistre import Sinistre
from app.models.hospital import Hospital
from app.models.souscription import Souscription
from app.models.questionnaire import Questionnaire
from app.models.notification import Notification
from app.models.prestation import Prestation
from app.schemas.alerte import AlerteCreate, AlerteResponse
from app.schemas.sinistre import (
    SinistreResponse,
    SinistreDetailResponse,
    HospitalInfo,
    PrestationInfo,
    SinistreWorkflowStepResponse,
    SinistreVerificationRequest,
)
from app.schemas.questionnaire import QuestionnaireResponse
from app.schemas.hospital_stay import HospitalStayResponse
from app.services.sinistre_workflow_service import ensure_workflow_steps, update_workflow_step
from pydantic import BaseModel
import uuid
import json
import asyncio
from typing import Dict, Set

router = APIRouter()

# Gestionnaire de connexions WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}  # user_id -> set of websockets
    
    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
    
    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
    
    async def send_personal_message(self, message: dict, user_id: int):
        if user_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.add(connection)
            # Nettoyer les connexions déconnectées
            for conn in disconnected:
                self.active_connections[user_id].discard(conn)
    
    async def broadcast_to_role(self, message: dict, role: Role):
        """Diffuser un message à tous les utilisateurs d'un rôle"""
        db = SessionLocal()
        try:
            users = db.query(User).filter(User.role == role, User.is_active == True).all()
            for user in users:
                await self.send_personal_message(message, user.id)
        finally:
            db.close()

manager = ConnectionManager()


def enrich_alerte_with_related_data(
    alerte: Alerte,
    sinistre: Optional[Sinistre] = None,
    hospital: Optional[Hospital] = None
):
    """Injecter les métadonnées (sinistre/hôpital) dans l'objet Alerte."""
    if sinistre:
        setattr(alerte, "sinistre_id", sinistre.id)
    else:
        setattr(alerte, "sinistre_id", None)
    
    if hospital:
        setattr(alerte, "assigned_hospital", hospital)
        try:
            distance_km = calculate_distance(
                alerte.latitude,
                alerte.longitude,
                hospital.latitude,
                hospital.longitude,
            )
            setattr(alerte, "distance_to_hospital_km", round(float(distance_km), 2))
        except Exception:
            setattr(alerte, "distance_to_hospital_km", None)
    else:
        setattr(alerte, "assigned_hospital", None)
        setattr(alerte, "distance_to_hospital_km", None)
    
    if hasattr(alerte, "user") and alerte.user:
        setattr(alerte, "user_full_name", alerte.user.full_name or alerte.user.username)
        setattr(alerte, "user_email", alerte.user.email)
        setattr(alerte, "user_telephone", getattr(alerte.user, "telephone", None))
        setattr(alerte, "user_photo_url", getattr(alerte.user, "photo_url", None))
        dn = getattr(alerte.user, "date_naissance", None)
        setattr(alerte, "user_date_naissance", dn.isoformat() if dn else None)
        setattr(alerte, "user_nom_contact_urgence", getattr(alerte.user, "nom_contact_urgence", None))
        setattr(alerte, "user_contact_urgence", getattr(alerte.user, "contact_urgence", None))
    else:
        setattr(alerte, "user_full_name", None)
        setattr(alerte, "user_email", None)
        setattr(alerte, "user_telephone", None)
        setattr(alerte, "user_photo_url", None)
        setattr(alerte, "user_date_naissance", None)
        setattr(alerte, "user_nom_contact_urgence", None)
        setattr(alerte, "user_contact_urgence", None)
    if hospital and getattr(hospital, "medecin_referent", None):
        med = hospital.medecin_referent
        setattr(alerte, "medecin_referent_nom", med.full_name or med.username or med.email)
        setattr(alerte, "medecin_referent_telephone", getattr(med, "telephone", None))
    else:
        setattr(alerte, "medecin_referent_nom", None)
        setattr(alerte, "medecin_referent_telephone", None)

    is_validated = False
    if sinistre:
        workflow_steps = getattr(sinistre, "workflow_steps", []) or []
        for step in workflow_steps:
            if step.step_key == "verification_urgence" and step.statut == StatutWorkflowSinistre.COMPLETED.value:
                is_validated = True
                break
    setattr(alerte, "is_validated", is_validated)

    is_oriented = bool(sinistre and getattr(sinistre, "hospital_stay", None) is not None)
    setattr(alerte, "is_oriented", is_oriented)


def calculate_distance(lat1: Decimal, lon1: Decimal, lat2: Decimal, lon2: Decimal) -> float:
    """Calculer la distance en kilomètres entre deux points GPS (formule de Haversine)"""
    from math import radians, sin, cos, sqrt, atan2
    
    R = 6371  # Rayon de la Terre en km
    
    lat1_rad = radians(float(lat1))
    lat2_rad = radians(float(lat2))
    delta_lat = radians(float(lat2) - float(lat1))
    delta_lon = radians(float(lon2) - float(lon1))
    
    a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    return R * c


def find_nearest_hospital(latitude: Decimal, longitude: Decimal, db: Session) -> Optional[Hospital]:
    """Trouver l'hôpital le plus proche"""
    hospitals = db.query(Hospital).filter(Hospital.est_actif == True).all()
    
    if not hospitals:
        return None
    
    nearest = None
    min_distance = float('inf')
    
    for hospital in hospitals:
        distance = calculate_distance(latitude, longitude, hospital.latitude, hospital.longitude)
        if distance < min_distance:
            min_distance = distance
            nearest = hospital
    
    return nearest


def user_has_hospital_access(user: User, sinistre: Optional[Sinistre], db: Session) -> bool:
    if not sinistre or not sinistre.hospital_id:
        return False
    if user.role in [Role.HOSPITAL_ADMIN, Role.AGENT_RECEPTION_HOPITAL, Role.MEDECIN_HOPITAL, Role.DOCTOR]:
        return bool(user.hospital_id and user.hospital_id == sinistre.hospital_id)
    if user.role == Role.MEDECIN_REFERENT_MH:
        if sinistre.medecin_referent_id and sinistre.medecin_referent_id == user.id:
            return True
        hospital = db.query(Hospital).filter(
            Hospital.id == sinistre.hospital_id,
            Hospital.medecin_referent_id == user.id
        ).first()
        return hospital is not None
    return False


def get_latest_questionnaire(
    db: Session,
    subscription_id: Optional[int],
    questionnaire_type: str = "medical"
) -> Optional[Questionnaire]:
    """Récupérer le questionnaire le plus récent d'une souscription pour un type donné."""
    if not subscription_id:
        return None
    
    return (
        db.query(Questionnaire)
        .filter(
            Questionnaire.souscription_id == subscription_id,
            Questionnaire.type_questionnaire == questionnaire_type,
            Questionnaire.statut != "archive"
        )
        .order_by(Questionnaire.version.desc(), Questionnaire.created_at.desc())
        .first()
    )


def _questionnaire_excerpt(questionnaire: Optional[Questionnaire]) -> Optional[str]:
    """Créer un extrait lisible du questionnaire pour les notifications."""
    if not questionnaire or not questionnaire.reponses:
        return None
    
    try:
        reponses = questionnaire.reponses
        if not isinstance(reponses, dict):
            return None
        
        lines = []
        
        # Maladies chroniques
        if reponses.get("chronicDiseases"):
            diseases = reponses["chronicDiseases"]
            if isinstance(diseases, list) and diseases:
                lines.append(f"• Maladies chroniques: {', '.join(diseases)}")
        
        # Traitements réguliers
        if reponses.get("regularTreatment") == "oui" and reponses.get("treatmentDetails"):
            lines.append(f"• Traitement en cours: {reponses['treatmentDetails']}")
        
        # Hospitalisations récentes
        if reponses.get("recentHospitalization") == "oui" and reponses.get("hospitalizationDetails"):
            lines.append(f"• Hospitalisation récente: {reponses['hospitalizationDetails']}")
        
        # Chirurgies récentes
        if reponses.get("recentSurgery") == "oui" and reponses.get("surgeryDetails"):
            lines.append(f"• Chirurgie récente: {reponses['surgeryDetails']}")
        
        # Symptômes
        if reponses.get("symptoms"):
            symptoms = reponses["symptoms"]
            if isinstance(symptoms, list) and symptoms:
                lines.append(f"• Symptômes: {', '.join(symptoms)}")
        
        # Maladies infectieuses
        if reponses.get("infectiousDiseases"):
            diseases = reponses["infectiousDiseases"]
            if isinstance(diseases, list) and diseases:
                lines.append(f"• Maladies infectieuses: {', '.join(diseases)}")
        
        # Sports à risque
        if reponses.get("riskySports"):
            sports = reponses["riskySports"]
            if isinstance(sports, list) and sports and sports[0] != "Aucun":
                lines.append(f"• Sports à risque: {', '.join(sports)}")
        
        # Équipement médical
        if reponses.get("medicalEquipment") == "oui" and reponses.get("equipmentDetails"):
            lines.append(f"• Équipement médical: {reponses['equipmentDetails']}")
        
        if not lines:
            return None
        
        result = "\n".join(lines)
        if len(result) > 500:
            return result[:500] + "..."
        return result
        
    except (TypeError, ValueError, KeyError) as e:
        return None


async def notify_hospital_reception(
    db: Session,
    sinistre: Sinistre,
    alerte: Alerte,
    hospital: Optional[Hospital],
    souscription: Optional[Souscription],
    assure: Optional[User],
    medical_questionnaire: Optional[Questionnaire] = None
):
    """Notifier la réception de l'hôpital assigné avec l'alerte et le dossier médical."""
    if not hospital:
        return
    
    recipients = db.query(User).filter(
        User.role == Role.AGENT_RECEPTION_HOPITAL,
        User.is_active == True,
        User.hospital_id == hospital.id
    ).all()

    if not recipients:
        recipients = db.query(User).filter(
            User.role == Role.AGENT_RECEPTION_HOPITAL,
            User.is_active == True,
            User.hospital_id.is_(None)
        ).all()
    
    if not souscription:
        souscription = db.query(Souscription).filter(
            Souscription.id == sinistre.souscription_id
        ).first()
    
    if not assure and souscription:
        assure = db.query(User).filter(User.id == souscription.user_id).first()
    
    assure_name = None
    if assure:
        assure_name = assure.full_name or assure.username or assure.email
    
    questionnaire_payload = None
    if medical_questionnaire:
        questionnaire_payload = {
            "id": medical_questionnaire.id,
            "type": medical_questionnaire.type_questionnaire,
            "version": medical_questionnaire.version,
            "statut": medical_questionnaire.statut,
            "reponses": medical_questionnaire.reponses,
            "updated_at": medical_questionnaire.updated_at.isoformat() if medical_questionnaire.updated_at else None,
        }
    
    hospital_payload = {
        "id": hospital.id,
        "nom": hospital.nom,
        "adresse": hospital.adresse,
        "ville": hospital.ville,
        "telephone": hospital.telephone,
        "email": hospital.email,
        "latitude": float(hospital.latitude) if hospital.latitude is not None else None,
        "longitude": float(hospital.longitude) if hospital.longitude is not None else None,
    }
    
    base_message = f"Alerte #{alerte.numero_alerte} assignée à {hospital.nom}.\n\n"
    base_message += f"📋 Informations:\n"
    base_message += f"• Priorité: {alerte.priorite.capitalize()}\n"
    base_message += f"• Adresse: {alerte.adresse or 'Non renseignée'}\n"
    if assure_name:
        base_message += f"• Assuré: {assure_name}\n"
    
    if medical_questionnaire:
        base_message += f"\n📄 Dossier médical #{medical_questionnaire.id} (version {medical_questionnaire.version}) disponible.\n"
    else:
        base_message += "\n⚠️ Aucun questionnaire médical n'est encore renseigné pour cet assuré.\n"
    
    for user in recipients:
        notification = Notification(
            user_id=user.id,
            type_notification="sos_alert_hospital",
            titre=f"Alerte SOS assignée à {hospital.nom}",
            message=base_message,
            lien_relation_id=sinistre.id,
            lien_relation_type="sinistre"
        )
        db.add(notification)
        db.flush()
        
        payload = {
            "type": "hospital_assignment",
            "alerte_id": alerte.id,
            "sinistre_id": sinistre.id,
            "numero_alerte": alerte.numero_alerte,
            "numero_sinistre": sinistre.numero_sinistre,
            "priorite": alerte.priorite,
            "description": alerte.description,
            "latitude": float(alerte.latitude) if alerte.latitude is not None else None,
            "longitude": float(alerte.longitude) if alerte.longitude is not None else None,
            "hospital": hospital_payload,
            "medical_questionnaire": questionnaire_payload,
        }
        await manager.send_personal_message(payload, user.id)
        
        try:
            from app.workers.tasks import send_notification_multi_channel
            send_notification_multi_channel.delay(
                user_id=user.id,
                notification_id=notification.id,
                channels=["email", "push"]
            )
        except Exception:
            pass
    
    if not recipients and hospital.email:
        try:
            from app.workers.tasks import send_email
            send_email.delay(
                to_email=hospital.email,
                subject=f"Alerte SOS assignée à {hospital.nom}",
                body_html=f"<p>{base_message.replace(chr(10), '<br>')}</p>",
                body_text=base_message
            )
        except Exception:
            pass


def generate_numero_sinistre() -> str:
    """Générer un numéro de sinistre unique"""
    return f"SIN-{uuid.uuid4().hex[:8].upper()}-{datetime.utcnow().strftime('%Y%m%d')}"


@router.post("/trigger", response_model=AlerteResponse, status_code=status.HTTP_201_CREATED)
async def trigger_sos(
    alerte_data: AlerteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Déclencher une alerte SOS.
    Crée une alerte, puis un sinistre, trouve l'hôpital le plus proche,
    et notifie les agents sinistre et médecins référents.
    """
    # Vérifier que l'utilisateur a une souscription active
    souscription = None
    if alerte_data.souscription_id:
        souscription = db.query(Souscription).filter(
            Souscription.id == alerte_data.souscription_id,
            Souscription.user_id == current_user.id,
            Souscription.statut == "active"
        ).first()
    else:
        # Chercher une souscription active pour l'utilisateur
        souscription = db.query(Souscription).filter(
            Souscription.user_id == current_user.id,
            Souscription.statut == "active"
        ).order_by(Souscription.created_at.desc()).first()
    
    if not souscription:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucune souscription active trouvée pour cet utilisateur"
        )
    
    # Générer un numéro d'alerte unique
    numero_alerte = f"ALERT-{uuid.uuid4().hex[:8].upper()}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    # Créer l'alerte
    alerte = Alerte(
        user_id=current_user.id,
        souscription_id=souscription.id,
        numero_alerte=numero_alerte,
        latitude=alerte_data.latitude,
        longitude=alerte_data.longitude,
        adresse=alerte_data.adresse,
        description=alerte_data.description,
        priorite=alerte_data.priorite,
        statut="en_attente"
    )
    
    db.add(alerte)
    db.commit()
    db.refresh(alerte)
    
    # Trouver l'hôpital le plus proche
    hospital = find_nearest_hospital(alerte_data.latitude, alerte_data.longitude, db)
    
    # Trouver un agent sinistre disponible (SOS_OPERATOR)
    agent_sinistre = db.query(User).filter(
        User.role == Role.SOS_OPERATOR,
        User.is_active == True
    ).first()
    
    # Trouver un médecin référent disponible
    medecin_referent = db.query(User).filter(
        User.role == Role.MEDECIN_REFERENT_MH,
        User.is_active == True
    ).first()
    
    if not medecin_referent:
        medecin_referent = db.query(User).filter(
            User.role == Role.DOCTOR,
            User.is_active == True
        ).first()
    
    # Créer le sinistre (numéro attribué lors de la validation médicale)
    sinistre = Sinistre(
        alerte_id=alerte.id,
        souscription_id=souscription.id,
        hospital_id=hospital.id if hospital else None,
        numero_sinistre=None,
        description=alerte_data.description,
        statut="en_cours",
        agent_sinistre_id=agent_sinistre.id if agent_sinistre else None,
        medecin_referent_id=medecin_referent.id if medecin_referent else None
    )
    
    db.add(sinistre)
    db.flush()
    
    # Mettre à jour le statut de l'alerte
    alerte.statut = "en_cours"
    
    # Créer des notifications pour l'agent sinistre et le médecin référent
    numero_sinistre_placeholder = "attribué après validation médicale"

    if agent_sinistre:
        assure_name = current_user.full_name or current_user.username or current_user.email
        hospital_name = hospital.nom if hospital else "Non assigné"
        notification_agent = Notification(
            user_id=agent_sinistre.id,
            type_notification="sos_alert_received",
            titre="Nouvelle alerte SOS reçue",
            message=f"📋 Informations:\n• Alerte: #{numero_alerte}\n• Priorité: {alerte.priorite.capitalize()}\n• Assuré: {assure_name}\n• Hôpital assigné: {hospital_name}\n• Adresse: {alerte.adresse or 'Non renseignée'}",
            lien_relation_id=sinistre.id,
            lien_relation_type="sinistre"
        )
        db.add(notification_agent)
        db.flush()  # Pour obtenir l'ID de la notification
        
        # Envoyer via WebSocket
        await manager.send_personal_message({
            "type": "new_alert",
            "alerte_id": alerte.id,
            "sinistre_id": sinistre.id,
            "numero_alerte": numero_alerte,
            "numero_sinistre": None,
            "latitude": float(alerte.latitude),
            "longitude": float(alerte.longitude),
            "description": alerte.description,
            "priorite": alerte.priorite,
            "timestamp": datetime.utcnow().isoformat()
        }, agent_sinistre.id)
        
        # Envoyer notification par email et push via Celery
        try:
            from app.workers.tasks import send_notification_multi_channel
            send_notification_multi_channel.delay(
                user_id=agent_sinistre.id,
                notification_id=notification_agent.id,
                channels=["email", "push"]
            )
        except Exception as e:
            # Si Celery n'est pas disponible, on continue
            pass
    
    if medecin_referent:
        assure_name = current_user.full_name or current_user.username or current_user.email
        hospital_name = hospital.nom if hospital else "Non assigné"
        priorite_label = alerte.priorite.capitalize() if alerte.priorite else "Normale"
        adresse = alerte.adresse or "Non renseignée"
        description = alerte.description or "Aucune description fournie"
        
        # Message structuré et informatif
        message_medecin = (
            f"🚨 Alerte SOS déclenchée - Intervention médicale requise\n\n"
            f"📋 Informations:\n"
            f"• Alerte: #{numero_alerte}\n"
            f"• Priorité: {priorite_label}\n"
            f"• Assuré: {assure_name}\n"
            f"• Hôpital assigné: {hospital_name}\n"
            f"• Adresse: {adresse}\n"
            f"• Description: {description}\n"
            f"• Sinistre: {numero_sinistre_placeholder}"
        )
        
        notification_medecin = Notification(
            user_id=medecin_referent.id,
            type_notification="sos_alert",
            titre="Nouvelle alerte SOS - Intervention médicale requise",
            message=message_medecin,
            lien_relation_id=sinistre.id,
            lien_relation_type="sinistre"
        )
        db.add(notification_medecin)
        db.flush()
        
        # Envoyer via WebSocket
        await manager.send_personal_message({
            "type": "new_alert",
            "alerte_id": alerte.id,
            "sinistre_id": sinistre.id,
            "numero_alerte": numero_alerte,
            "numero_sinistre": None,
            "latitude": float(alerte.latitude),
            "longitude": float(alerte.longitude),
            "description": alerte.description,
            "priorite": alerte.priorite,
            "timestamp": datetime.utcnow().isoformat()
        }, medecin_referent.id)
        
        # Envoyer notification par email et push via Celery
        try:
            from app.workers.tasks import send_notification_multi_channel
            send_notification_multi_channel.delay(
                user_id=medecin_referent.id,
                notification_id=notification_medecin.id,
                channels=["email", "push"]
            )
        except Exception as e:
            # Si Celery n'est pas disponible, on continue
            pass
    
    medical_questionnaire = get_latest_questionnaire(db, souscription.id)
    await notify_hospital_reception(
        db=db,
        sinistre=sinistre,
        alerte=alerte,
        hospital=hospital,
        souscription=souscription,
        assure=current_user,
        medical_questionnaire=medical_questionnaire
    )
    
    ensure_workflow_steps(db, sinistre, alerte)

    db.commit()
    db.refresh(alerte)
    enrich_alerte_with_related_data(alerte, sinistre, hospital)
    
    return alerte


# Statuts considérés comme "clôturés" : à exclure de la liste "alertes en temps réel"
ALERTE_STATUTS_CLOTURES = {"resolue", "annulee"}


@router.get("", response_model=List[AlerteResponse])
@router.get("/", response_model=List[AlerteResponse])
async def get_alertes(
    skip: int = 0,
    limit: int = 100,
    statut: Optional[str] = None,
    realtime: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir la liste des alertes. Si realtime=true, exclut les alertes clôturées (resolue, annulee)."""
    query = db.query(Alerte).options(joinedload(Alerte.user))
    
    # Les utilisateurs normaux ne voient que leurs alertes
    if current_user.role not in [Role.ADMIN, Role.SOS_OPERATOR, Role.DOCTOR]:
        hospital_ids: list[int] = []
        if current_user.role in [Role.HOSPITAL_ADMIN, Role.AGENT_RECEPTION_HOPITAL, Role.MEDECIN_HOPITAL]:
            if current_user.hospital_id:
                hospital_ids.append(current_user.hospital_id)
        if current_user.role == Role.MEDECIN_REFERENT_MH:
            med_hospitals = db.query(Hospital.id).filter(
                Hospital.medecin_referent_id == current_user.id
            ).all()
            hospital_ids.extend([row[0] for row in med_hospitals])
            if current_user.hospital_id:
                hospital_ids.append(current_user.hospital_id)
        hospital_ids = list(set([hid for hid in hospital_ids if hid]))
        
        if hospital_ids:
            query = query.join(Sinistre, Sinistre.alerte_id == Alerte.id).filter(
                Sinistre.hospital_id.in_(hospital_ids)
            )
        else:
            if current_user.role in [Role.HOSPITAL_ADMIN, Role.AGENT_RECEPTION_HOPITAL, Role.MEDECIN_REFERENT_MH, Role.MEDECIN_HOPITAL]:
                # Aucun hôpital assigné : aucune alerte
                query = query.filter(False)
            else:
                query = query.filter(Alerte.user_id == current_user.id)
    
    if statut:
        query = query.filter(Alerte.statut == statut)
    if realtime:
        query = query.filter(Alerte.statut.notin_(ALERTE_STATUTS_CLOTURES))
    
    alertes = query.order_by(Alerte.created_at.desc()).offset(skip).limit(limit).all()
    
    if not alertes:
        return alertes
    
    alerte_ids = [alerte.id for alerte in alertes]
    sinistres = (
        db.query(Sinistre)
        .options(
            selectinload(Sinistre.workflow_steps),
            selectinload(Sinistre.hospital_stay),
        )
        .filter(Sinistre.alerte_id.in_(alerte_ids))
        .all()
    )
    sinistre_map = {sinistre.alerte_id: sinistre for sinistre in sinistres}

    hospital_ids = [sinistre.hospital_id for sinistre in sinistres if sinistre.hospital_id]
    hospital_map = {}
    if hospital_ids:
        hospitals = (
            db.query(Hospital)
            .options(joinedload(Hospital.medecin_referent))
            .filter(Hospital.id.in_(hospital_ids))
            .all()
        )
        hospital_map = {hospital.id: hospital for hospital in hospitals}

    souscription_ids = [a.souscription_id for a in alertes if a.souscription_id]
    souscription_map = {}
    if souscription_ids:
        souscriptions = db.query(Souscription).filter(Souscription.id.in_(souscription_ids)).all()
        souscription_map = {s.id: s.numero_souscription for s in souscriptions}

    for alerte in alertes:
        sinistre = sinistre_map.get(alerte.id)
        hospital = None
        if sinistre and sinistre.hospital_id:
            hospital = hospital_map.get(sinistre.hospital_id)
        enrich_alerte_with_related_data(alerte, sinistre, hospital)
        setattr(
            alerte,
            "numero_souscription",
            souscription_map.get(alerte.souscription_id) if alerte.souscription_id else None,
        )
        steps = []
        if sinistre:
            steps_orm, _ = ensure_workflow_steps(db, sinistre, alerte)
            for s in sorted(steps_orm, key=lambda x: x.ordre):
                steps.append({
                    "step_key": s.step_key,
                    "titre": s.titre,
                    "ordre": s.ordre,
                    "statut": s.statut,
                    "completed_at": getattr(s, "completed_at", None),
                })
        setattr(alerte, "workflow_steps", steps)

    return alertes


@router.get("/{alerte_id}", response_model=AlerteResponse)
async def get_alerte(
    alerte_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir une alerte par ID"""
    alerte = (
        db.query(Alerte)
        .options(joinedload(Alerte.user))
        .filter(Alerte.id == alerte_id)
        .first()
    )
    
    if not alerte:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alerte non trouvée"
        )
    
    sinistre = db.query(Sinistre).filter(Sinistre.alerte_id == alerte_id).first()
    allowed_roles = [Role.ADMIN, Role.SOS_OPERATOR, Role.DOCTOR, Role.MEDECIN_HOPITAL]
    if current_user.role not in allowed_roles:
        if alerte.user_id != current_user.id and not user_has_hospital_access(current_user, sinistre, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé"
            )
    elif current_user.role in [Role.DOCTOR, Role.MEDECIN_HOPITAL]:
        if not user_has_hospital_access(current_user, sinistre, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé à ce dossier"
            )
    hospital = None
    if sinistre and sinistre.hospital_id:
        hospital = (
            db.query(Hospital)
            .options(joinedload(Hospital.medecin_referent))
            .filter(Hospital.id == sinistre.hospital_id)
            .first()
        )
    enrich_alerte_with_related_data(alerte, sinistre, hospital)
    if alerte.souscription_id:
        souscription = db.query(Souscription).filter(Souscription.id == alerte.souscription_id).first()
        if souscription:
            setattr(alerte, "numero_souscription", souscription.numero_souscription)
    else:
        setattr(alerte, "numero_souscription", None)

    return alerte


@router.get("/{alerte_id}/sinistre", response_model=SinistreDetailResponse)
async def get_sinistre_by_alerte(
    alerte_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtenir les détails complets du sinistre associé à une alerte"""
    alerte = (
        db.query(Alerte)
        .options(joinedload(Alerte.user))
        .filter(Alerte.id == alerte_id)
        .first()
    )
    
    if not alerte:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alerte non trouvée"
        )
    
    # Récupérer le sinistre associé
    sinistre = db.query(Sinistre).filter(Sinistre.alerte_id == alerte_id).first()
    
    allowed_roles = [Role.ADMIN, Role.SOS_OPERATOR, Role.DOCTOR, Role.MEDECIN_HOPITAL]
    if current_user.role not in allowed_roles:
        if alerte.user_id != current_user.id and not user_has_hospital_access(current_user, sinistre, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé"
            )
    elif current_user.role in [Role.DOCTOR, Role.MEDECIN_HOPITAL]:
        if not sinistre or not user_has_hospital_access(current_user, sinistre, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé à ce dossier"
            )
    
    if not sinistre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sinistre non trouvé pour cette alerte"
        )
    
    # Récupérer l'hôpital si disponible
    hospital_info = None
    if sinistre.hospital_id:
        hospital = db.query(Hospital).filter(Hospital.id == sinistre.hospital_id).first()
        if hospital:
            hospital_info = HospitalInfo(
                id=hospital.id,
                nom=hospital.nom,
                adresse=hospital.adresse,
                ville=hospital.ville,
                pays=hospital.pays,
                telephone=hospital.telephone,
                email=hospital.email,
                latitude=hospital.latitude,
                longitude=hospital.longitude
            )
    
    # Récupérer les prestations (interventions)
    prestations = db.query(Prestation).filter(Prestation.sinistre_id == sinistre.id).all()
    prestations_info = [
        PrestationInfo(
            id=p.id,
            code_prestation=p.code_prestation,
            libelle=p.libelle,
            description=p.description,
            montant_unitaire=p.montant_unitaire,
            quantite=p.quantite,
            montant_total=p.montant_total,
            date_prestation=p.date_prestation,
            statut=p.statut
        )
        for p in prestations
    ]
    
    # Récupérer les noms des agents
    agent_sinistre_nom = None
    if sinistre.agent_sinistre_id:
        agent = db.query(User).filter(User.id == sinistre.agent_sinistre_id).first()
        if agent:
            agent_sinistre_nom = agent.full_name or agent.username or agent.email
    
    medecin_referent_nom = None
    if sinistre.medecin_referent_id:
        medecin = db.query(User).filter(User.id == sinistre.medecin_referent_id).first()
        if medecin:
            medecin_referent_nom = medecin.full_name or medecin.username or medecin.email

    workflow_steps, workflow_modified = ensure_workflow_steps(db, sinistre, alerte)
    if workflow_modified:
        db.commit()
        db.refresh(sinistre)
    else:
        db.flush()

    medical_questionnaire_payload = None
    if sinistre.souscription_id:
        latest_questionnaire = get_latest_questionnaire(db, sinistre.souscription_id)
        if latest_questionnaire:
            medical_questionnaire_payload = QuestionnaireResponse.model_validate(latest_questionnaire)
    
    patient_info = None
    if hasattr(alerte, "user") and alerte.user:
        patient_info = {
            "id": alerte.user.id,
            "full_name": alerte.user.full_name or alerte.user.username,
            "email": alerte.user.email
        }

    hospital_stay_payload = None
    if sinistre.hospital_stay:
        hospital_stay_payload = HospitalStayResponse.model_validate(sinistre.hospital_stay)

    numero_souscription = None
    if sinistre.souscription_id:
        souscription = db.query(Souscription).filter(Souscription.id == sinistre.souscription_id).first()
        if souscription:
            numero_souscription = souscription.numero_souscription

    return SinistreDetailResponse(
        id=sinistre.id,
        alerte_id=sinistre.alerte_id,
        souscription_id=sinistre.souscription_id,
        numero_souscription=numero_souscription,
        hospital_id=sinistre.hospital_id,
        numero_sinistre=sinistre.numero_sinistre,
        description=sinistre.description,
        statut=sinistre.statut,
        agent_sinistre_id=sinistre.agent_sinistre_id,
        medecin_referent_id=sinistre.medecin_referent_id,
        notes=sinistre.notes,
        created_at=sinistre.created_at,
        updated_at=sinistre.updated_at,
        hospital=hospital_info,
        prestations=prestations_info,
        agent_sinistre_nom=agent_sinistre_nom,
        medecin_referent_nom=medecin_referent_nom,
        workflow_steps=workflow_steps,
        medical_questionnaire=medical_questionnaire_payload,
        patient=patient_info,
        hospital_stay=hospital_stay_payload,
    )


@router.post(
    "/sinistres/{sinistre_id}/verification",
    response_model=SinistreWorkflowStepResponse,
    status_code=status.HTTP_200_OK,
)
async def verify_alert_veracity(
    sinistre_id: int,
    verification: SinistreVerificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Permettre à un médecin référent de confirmer ou refuser la véracité d'une alerte.
    Cette action met à jour l'étape `verification_urgence` du workflow sinistre.
    """
    allowed_roles = {Role.MEDECIN_REFERENT_MH}
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux médecins référents."
        )

    sinistre = db.query(Sinistre).filter(Sinistre.id == sinistre_id).first()
    if not sinistre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sinistre non trouvé"
        )

    alerte = db.query(Alerte).filter(Alerte.id == sinistre.alerte_id).first()

    if not user_has_hospital_access(current_user, sinistre, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé à ce sinistre"
        )

    target_status = (
        StatutWorkflowSinistre.COMPLETED if verification.approve else StatutWorkflowSinistre.CANCELLED
    )

    try:
        step = update_workflow_step(
            db=db,
            sinistre=sinistre,
            alerte=alerte,
            step_key="verification_urgence",
            statut=target_status,
            actor_id=current_user.id,
            notes=verification.notes,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Étape de vérification introuvable pour ce sinistre."
        )

    if verification.approve:
        if sinistre.statut == "annule":
            sinistre.statut = "en_cours"
            if alerte and alerte.statut == "annulee":
                alerte.statut = "en_cours"
        if not sinistre.numero_sinistre:
            sinistre.numero_sinistre = generate_numero_sinistre()
        
        # Notifier les agents de réception de l'hôpital que l'alerte est validée
        if sinistre.hospital_id:
            hospital = db.query(Hospital).filter(Hospital.id == sinistre.hospital_id).first()
            if hospital:
                recipients = db.query(User).filter(
                    User.role == Role.AGENT_RECEPTION_HOPITAL,
                    User.is_active == True,  # noqa: E712
                    User.hospital_id == hospital.id
                ).all()
                
                if not recipients:
                    recipients = db.query(User).filter(
                        User.role == Role.AGENT_RECEPTION_HOPITAL,
                        User.is_active == True,  # noqa: E712
                        User.hospital_id.is_(None)
                    ).all()
                
                alerte_label = alerte.numero_alerte if alerte else f"Alerte #{sinistre.alerte_id}"
                sinistre_label = sinistre.numero_sinistre or f"Sinistre #{sinistre.id}"
                
                for user in recipients:
                    notification = Notification(
                        user_id=user.id,
                        type_notification="alert_validated_by_referent",
                        titre="Alerte validée par le médecin référent",
                        message=f"L'alerte {alerte_label} (sinistre {sinistre_label}) a été validée par le médecin référent MH. Vous pouvez maintenant orienter l'assuré vers un médecin hospitalier.",
                        lien_relation_id=sinistre.id,
                        lien_relation_type="sinistre"
                    )
                    db.add(notification)
    else:
        sinistre.statut = "annule"
        if alerte:
            alerte.statut = "annulee"

    db.commit()
    db.refresh(step)

    return step

