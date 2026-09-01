"""
API IA - Module d'analyse pour Agent de Production
Mobility Health
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
import tempfile
import os
import shutil
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.assureur import Assureur

# Import du module IA
from app.ia_module import analyser_document, formater_pour_agent_production, router_assureur, storage_analyses

router = APIRouter(prefix="/ia", tags=["IA - Analyse Documents"])


# ═══════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════

class StatutMedical(BaseModel):
    """Statut de validation médicale (fourni par le Médecin MH)"""
    statut: str = "EN_ATTENTE"  # EN_ATTENTE, APPROUVE, REJETE
    approuve_par: Optional[str] = None
    date_approbation: Optional[str] = None
    commentaire: Optional[str] = None


class AnalyseRequest(BaseModel):
    """Requête d'analyse avec statut médical optionnel"""
    demande_id: Optional[str] = None
    statut_medical: Optional[StatutMedical] = None


class AnalyseResponse(BaseModel):
    """Réponse d'analyse IA"""
    success: bool
    message: str
    data: Optional[dict] = None


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.post("/analyser-documents", response_model=AnalyseResponse)
async def analyser_documents(
    fichiers: List[UploadFile] = File(...),
    demande_id: Optional[str] = None,
    souscription_id: Optional[int] = None,
    questionnaire_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🔍 Analyse des documents pour l'Agent de Production
    
    - Accepte plusieurs fichiers (PDF, images)
    - Effectue l'OCR et l'extraction d'informations
    - Sauvegarde les résultats dans la base de données
    - Retourne un résumé complet pour la décision
    
    **Rôles autorisés**: Agent de Production, Admin
    """
    
    # Vérifier le rôle (à adapter selon votre système de rôles)
    # if current_user.role not in ["agent_production", "admin", "super_admin"]:
    #     raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    if not fichiers:
        raise HTTPException(status_code=400, detail="Aucun fichier fourni")
    
    # Générer un demande_id si non fourni
    if not demande_id:
        from datetime import datetime
        demande_id = f"DEM-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    resultats_analyse = []
    fichiers_temp = []
    
    try:
        # Sauvegarder les fichiers temporairement
        for fichier in fichiers:
            # Créer un fichier temporaire
            suffix = os.path.splitext(fichier.filename)[1]
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            
            # Copier le contenu
            content = await fichier.read()
            temp_file.write(content)
            temp_file.close()
            
            fichiers_temp.append({
                "path": temp_file.name,
                "original_name": fichier.filename
            })
        
        # Analyser chaque fichier
        for fichier_info in fichiers_temp:
            try:
                resultat = analyser_document(fichier_info["path"])
                # Emballer le résultat dans le format attendu par le formateur
                resultats_analyse.append({
                    "status": resultat.get("status", "ok"),
                    "nom_fichier": fichier_info["original_name"],
                    "analyse": resultat  # Le formateur attend les données sous "analyse"
                })
            except Exception as e:
                resultats_analyse.append({
                    "status": "error",
                    "nom_fichier": fichier_info["original_name"],
                    "erreur": str(e)
                })
        
        # Formater pour l'Agent de Production
        resultat_final = formater_pour_agent_production(
            resultats_analyse=resultats_analyse,
            demande_id=demande_id
        )
        
        # Déterminer les assureurs concernés
        # Extraire les infos personnelles et voyage du résultat
        infos_perso = resultat_final.get("infos_personnelles", {})
        infos_voyage = resultat_final.get("infos_voyage", {})
        
        # Utiliser router_assureur pour déterminer les assureurs concernés
        assureurs_router = router_assureur.router_demande(
            infos_personnelles=infos_perso,
            infos_voyage=infos_voyage
        )
        
        # Mapper les assureurs du router vers les IDs de la base de données
        # Pour l'instant, on récupère tous les assureurs de la base
        # TODO: Améliorer le mapping entre router_assureur et la base de données
        assureurs_db = db.query(Assureur).all()
        assureurs_concernes = []
        
        # Si on trouve des correspondances par nom, on les utilise
        # Sinon, on prend tous les assureurs (à améliorer selon vos besoins)
        for assureur_router in assureurs_router:
            # Chercher un assureur correspondant par nom
            assureur_trouve = next(
                (a for a in assureurs_db if a.nom.lower() == assureur_router.nom.lower()),
                None
            )
            if assureur_trouve:
                assureurs_concernes.append({"id": assureur_trouve.id, "nom": assureur_trouve.nom})
        
        # Si aucun assureur trouvé, prendre tous les assureurs (fallback)
        if not assureurs_concernes and assureurs_db:
            assureurs_concernes = [{"id": a.id, "nom": a.nom} for a in assureurs_db]
        
        # Sauvegarder l'analyse dans la base de données
        try:
            storage_analyses.sauvegarder_analyse(
                demande_id=demande_id,
                assureurs_concernes=assureurs_concernes,
                resultat_complet=resultat_final,
                db=db,
                souscription_id=souscription_id,
                questionnaire_id=questionnaire_id
            )
        except Exception as e:
            # Log l'erreur mais ne bloque pas la réponse
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"❌ Erreur lors de la sauvegarde de l'analyse: {e}", exc_info=True)
        
        return AnalyseResponse(
            success=True,
            message=f"{len(fichiers)} document(s) analysé(s) avec succès",
            data=resultat_final
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'analyse: {str(e)}"
        )
    
    finally:
        # Nettoyer les fichiers temporaires
        for fichier_info in fichiers_temp:
            try:
                os.unlink(fichier_info["path"])
            except:
                pass


@router.post("/analyser-avec-statut-medical", response_model=AnalyseResponse)
async def analyser_avec_statut_medical(
    fichiers: List[UploadFile] = File(...),
    demande_id: Optional[str] = None,
    statut_medical_json: Optional[str] = None,
    souscription_id: Optional[int] = None,
    questionnaire_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🔍 Analyse avec statut médical pré-rempli
    
    Utilisé quand le Médecin MH a déjà validé le dossier médical.
    
    **Paramètres**:
    - fichiers: Documents à analyser
    - demande_id: ID de la demande de souscription
    - statut_medical_json: JSON du statut médical (optionnel)
    """
    import json
    
    statut_medical = None
    if statut_medical_json:
        try:
            statut_medical = json.loads(statut_medical_json)
        except:
            pass
    
    if not fichiers:
        raise HTTPException(status_code=400, detail="Aucun fichier fourni")
    
    resultats_analyse = []
    fichiers_temp = []
    
    try:
        for fichier in fichiers:
            suffix = os.path.splitext(fichier.filename)[1]
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            content = await fichier.read()
            temp_file.write(content)
            temp_file.close()
            fichiers_temp.append({
                "path": temp_file.name,
                "original_name": fichier.filename
            })
        
        for fichier_info in fichiers_temp:
            try:
                resultat = analyser_document(fichier_info["path"])
                resultats_analyse.append({
                    "status": resultat.get("status", "ok"),
                    "nom_fichier": fichier_info["original_name"],
                    "analyse": resultat
                })
            except Exception as e:
                resultats_analyse.append({
                    "status": "error",
                    "nom_fichier": fichier_info["original_name"],
                    "erreur": str(e)
                })
        
        resultat_final = formater_pour_agent_production(
            resultats_analyse=resultats_analyse,
            demande_id=demande_id,
            statut_medical=statut_medical
        )
        
        # Générer un demande_id si non fourni
        if not demande_id:
            from datetime import datetime
            demande_id = f"DEM-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Déterminer les assureurs concernés
        infos_perso = resultat_final.get("infos_personnelles", {})
        infos_voyage = resultat_final.get("infos_voyage", {})
        
        assureurs_router = router_assureur.router_demande(
            infos_personnelles=infos_perso,
            infos_voyage=infos_voyage
        )
        
        # Mapper vers les IDs de la base de données
        assureurs_db = db.query(Assureur).all()
        assureurs_concernes = []
        
        for assureur_router in assureurs_router:
            assureur_trouve = next(
                (a for a in assureurs_db if a.nom.lower() == assureur_router.nom.lower()),
                None
            )
            if assureur_trouve:
                assureurs_concernes.append({"id": assureur_trouve.id, "nom": assureur_trouve.nom})
        
        if not assureurs_concernes and assureurs_db:
            assureurs_concernes = [{"id": a.id, "nom": a.nom} for a in assureurs_db]
        
        # Sauvegarder l'analyse
        try:
            storage_analyses.sauvegarder_analyse(
                demande_id=demande_id,
                assureurs_concernes=assureurs_concernes,
                resultat_complet=resultat_final,
                db=db,
                souscription_id=souscription_id,
                questionnaire_id=questionnaire_id
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"❌ Erreur lors de la sauvegarde de l'analyse: {e}", exc_info=True)
        
        return AnalyseResponse(
            success=True,
            message=f"{len(fichiers)} document(s) analysé(s)",
            data=resultat_final
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur: {str(e)}"
        )
    
    finally:
        for fichier_info in fichiers_temp:
            try:
                os.unlink(fichier_info["path"])
            except:
                pass


@router.get("/souscriptions/{subscription_id}/analyse")
async def get_subscription_ia_analysis(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🔍 Récupère le rapport d'analyse IA pour une souscription
    
    **Rôles autorisés**: Agent de Production, Admin, Médecin MH, Agent Technique
    """
    from app.models.souscription import Souscription
    from app.models.ia_analysis import IAAnalysis
    from app.core.enums import Role
    
    # Vérifier que la souscription existe
    souscription = db.query(Souscription).filter(
        Souscription.id == subscription_id
    ).first()
    
    if not souscription:
        raise HTTPException(
            status_code=404,
            detail="Souscription non trouvée"
        )
    
    # Vérifier les permissions
    allowed_roles = {
        Role.PRODUCTION_AGENT,
        Role.ADMIN,
        Role.MEDICAL_REVIEWER,
        Role.TECHNICAL_REVIEWER
    }
    
    if current_user.role not in allowed_roles and souscription.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Accès non autorisé"
        )
    
    # Récupérer l'analyse IA
    analyse = db.query(IAAnalysis).filter(
        IAAnalysis.souscription_id == subscription_id
    ).order_by(IAAnalysis.date_analyse.desc()).first()
    
    if not analyse:
        return {
            "success": False,
            "message": "Aucune analyse IA disponible pour cette souscription",
            "data": None
        }
    
    # Formater la réponse
    return {
        "success": True,
        "message": "Analyse IA récupérée avec succès",
        "data": {
            "demande_id": analyse.demande_id,
            "date_analyse": analyse.date_analyse.isoformat(),
            "client": {
                "nom": analyse.client_nom,
                "prenom": analyse.client_prenom,
                "pays": analyse.client_pays,
                "email": analyse.client_email
            },
            "scores": {
                "probabilite_acceptation": float(analyse.probabilite_acceptation),
                "probabilite_fraude": float(analyse.probabilite_fraude),
                "probabilite_confiance_assureur": float(analyse.probabilite_confiance_assureur),
                "score_coherence": float(analyse.score_coherence),
                "score_risque": float(analyse.score_risque),
                "score_confiance": float(analyse.score_confiance)
            },
            "evaluation": {
                "avis": analyse.avis,
                "niveau_risque": analyse.niveau_risque,
                "niveau_fraude": analyse.niveau_fraude,
                "niveau_confiance_assureur": analyse.niveau_confiance_assureur,
                "facteurs_risque": analyse.facteurs_risque or [],
                "signaux_fraude": analyse.signaux_fraude or [],
                "incoherences": analyse.incoherences or [],
                "message_ia": analyse.message_ia
            },
            "infos_personnelles": analyse.infos_personnelles or {},
            "infos_sante": analyse.infos_sante or {},
            "infos_voyage": analyse.infos_voyage or {},
            "documents_analyses": [
                {
                    "nom_fichier": doc.nom_fichier,
                    "type_document": doc.type_document,
                    "confiance_ocr": float(doc.confiance_ocr) if doc.confiance_ocr else None,
                    "est_expire": bool(doc.est_expire) if doc.est_expire is not None else False,
                    "qualite_ok": bool(doc.qualite_ok) if doc.qualite_ok is not None else True,
                    "est_complet": bool(doc.est_complet) if doc.est_complet is not None else True,
                    "est_coherent": bool(doc.est_coherent) if doc.est_coherent is not None else True
                }
                for doc in analyse.documents
            ],
            "assureurs_concernes": [
                {
                    "id": lia.assureur_id,
                    "nom": lia.assureur.nom if lia.assureur else "N/A",
                    "notifie": lia.notifie
                }
                for lia in analyse.assureurs_concernes
            ],
            "resultat_complet": analyse.resultat_complet
        }
    }


@router.get("/health")
async def health_check():
    """Vérification que le module IA est opérationnel"""
    try:
        from app.ia_module import analyser_document
        return {
            "status": "ok",
            "module": "ia_module",
            "message": "Module IA opérationnel"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

