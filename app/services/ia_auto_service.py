"""
Service pour déclencher automatiquement l'analyse IA lors du paiement
"""
import logging
import tempfile
import os
import base64
import re
import json
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.souscription import Souscription
from app.models.questionnaire import Questionnaire
from app.models.projet_voyage import ProjetVoyage
from app.models.projet_voyage_document import ProjetVoyageDocument
from app.services.minio_service import MinioService
from app.ia_module import analyser_document, formater_pour_agent_production, router_assureur, storage_analyses
from app.models.assureur import Assureur
from app.services.notification_service import NotificationService
from app.core.enums import Role

logger = logging.getLogger(__name__)


class IAAutoService:
    """Service pour déclencher automatiquement l'analyse IA"""
    
    @staticmethod
    def collect_subscription_documents(
        db: Session,
        souscription: Souscription
    ) -> List[Dict[str, Any]]:
        """
        Collecte tous les documents d'une souscription pour l'analyse IA
        
        Returns:
            Liste de dictionnaires avec {'path': chemin_fichier, 'original_name': nom}
        """
        documents = []
        
        try:
            # 1. Récupérer les documents du projet de voyage
            if souscription.projet_voyage_id:
                projet = db.query(ProjetVoyage).filter(
                    ProjetVoyage.id == souscription.projet_voyage_id
                ).first()
                
                if projet:
                    projet_docs = db.query(ProjetVoyageDocument).filter(
                        ProjetVoyageDocument.projet_voyage_id == projet.id
                    ).all()
                    
                    for doc in projet_docs:
                        # Télécharger depuis MinIO
                        file_bytes = MinioService.get_file(
                            doc.bucket_name,
                            doc.object_name
                        )
                        
                        if file_bytes:
                            # Créer un fichier temporaire
                            suffix = os.path.splitext(doc.display_name)[1] or '.pdf'
                            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                            temp_file.write(file_bytes)
                            temp_file.close()
                            
                            documents.append({
                                'path': temp_file.name,
                                'original_name': doc.display_name,
                                'type': 'projet_voyage'
                            })
            
            # 2. Récupérer les documents depuis les questionnaires
            questionnaires = db.query(Questionnaire).filter(
                Questionnaire.souscription_id == souscription.id
            ).all()
            
            for questionnaire in questionnaires:
                if questionnaire.reponses:
                    # Convertir en dict si nécessaire (SQLAlchemy peut retourner un objet JSON)
                    reponses_dict = questionnaire.reponses
                    if hasattr(reponses_dict, '__dict__'):
                        reponses_dict = dict(reponses_dict)
                    elif not isinstance(reponses_dict, dict):
                        try:
                            import json
                            if isinstance(reponses_dict, str):
                                reponses_dict = json.loads(reponses_dict)
                        except:
                            logger.warning(f"Impossible de convertir les réponses du questionnaire {questionnaire.id} en dictionnaire")
                            continue
                    
                    # Chercher les URLs de fichiers dans les réponses
                    # Structure typique: reponses.personal.photoIdentity, reponses.technical.documents, etc.
                    def extract_file_urls(data: Any, prefix: str = "") -> List[Dict[str, str]]:
                        """Extrait récursivement les URLs de fichiers depuis un dictionnaire"""
                        urls = []
                        if isinstance(data, dict):
                            for key, value in data.items():
                                current_path = f"{prefix}.{key}" if prefix else key
                                if isinstance(value, str):
                                    # Vérifier si c'est une URL (MinIO, HTTP) ou une image base64
                                    is_base64 = value.startswith('data:image') or 'base64' in value.lower()
                                    is_url = value.startswith('http') or (('/' in value) and not is_base64)
                                    
                                    if is_url or is_base64:
                                        urls.append({
                                            'url': value,
                                            'path': current_path,
                                            'name': key
                                        })
                                elif isinstance(value, (dict, list)):
                                    urls.extend(extract_file_urls(value, current_path))
                        elif isinstance(data, list):
                            for idx, item in enumerate(data):
                                urls.extend(extract_file_urls(item, f"{prefix}[{idx}]"))
                        return urls
                    
                    file_urls = extract_file_urls(reponses_dict)
                    logger.info(f"📋 {len(file_urls)} fichier(s) trouvé(s) dans le questionnaire {questionnaire.id}")
                    
                    # Télécharger les fichiers depuis MinIO ou décoder les images base64
                    for file_info in file_urls:
                        logger.info(f"🔍 Traitement du fichier: {file_info['name']} (chemin: {file_info['path']})")
                        url = file_info['url']
                        file_bytes = None
                        suffix = os.path.splitext(file_info['name'])[1] or '.jpg'
                        
                        # Vérifier si c'est une image base64
                        if url.startswith('data:image') or 'base64' in url.lower():
                            try:
                                # Extraire le type MIME et les données base64
                                # Format: data:image/jpeg;base64,/9j/4AAQ...
                                match = re.match(r'data:image/(\w+);base64,(.+)', url)
                                if match:
                                    image_format = match.group(1)
                                    base64_data = match.group(2)
                                    
                                    # Décoder l'image base64
                                    file_bytes = base64.b64decode(base64_data)
                                    
                                    # Déterminer l'extension
                                    format_map = {'jpeg': '.jpg', 'jpg': '.jpg', 'png': '.png', 'gif': '.gif', 'webp': '.webp'}
                                    suffix = format_map.get(image_format.lower(), '.jpg')
                                    logger.info(f"📷 Image base64 détectée et décodée: {file_info['name']} ({image_format})")
                                else:
                                    # Format alternatif: jpeg;base64,/9j/4AAQ...
                                    if 'base64' in url.lower():
                                        parts = url.split(',', 1)
                                        if len(parts) == 2:
                                            base64_data = parts[1]
                                            file_bytes = base64.b64decode(base64_data)
                                            logger.info(f"📷 Image base64 détectée et décodée (format alternatif): {file_info['name']}")
                            except Exception as e:
                                logger.warning(f"Erreur lors du décodage de l'image base64 {file_info['name']}: {e}")
                                continue
                        
                        # Sinon, essayer de récupérer depuis MinIO
                        elif '/' in url and not url.startswith('http'):
                            # C'est probablement un chemin MinIO
                            parts = url.split('/', 1)
                            if len(parts) == 2:
                                bucket_name = parts[0]
                                object_name = parts[1]
                                
                                try:
                                    file_bytes = MinioService.get_file(bucket_name, object_name)
                                except Exception as e:
                                    logger.warning(f"Erreur lors de la récupération du fichier {url} depuis Minio: {e}")
                        
                        # Si on a récupéré des données, créer le fichier temporaire
                        if file_bytes:
                            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                            temp_file.write(file_bytes)
                            temp_file.close()
                            
                            documents.append({
                                'path': temp_file.name,
                                'original_name': file_info['name'],
                                'type': f'questionnaire_{questionnaire.type_questionnaire}'
                            })
                            logger.info(f"✅ Document collecté: {file_info['name']}")
        
        except Exception as e:
            logger.error(f"Erreur lors de la collecte des documents: {e}", exc_info=True)
        
        return documents
    
    @staticmethod
    def _extract_questionnaire_data(
        db: Session,
        souscription: Souscription
    ) -> Dict[str, Any]:
        """
        Extrait les informations depuis les questionnaires (JSON, pas besoin d'OCR)
        
        Returns:
            Dictionnaire avec infos_personnelles, infos_sante, infos_voyage
        """
        infos_personnelles = {}
        infos_sante = {}
        infos_voyage = {}
        questionnaires_utilises = []
        
        try:
            questionnaires = db.query(Questionnaire).filter(
                Questionnaire.souscription_id == souscription.id
            ).all()
            
            for questionnaire in questionnaires:
                if not questionnaire.reponses:
                    continue
                
                # Convertir en dict si nécessaire
                reponses = questionnaire.reponses
                if hasattr(reponses, '__dict__'):
                    reponses = dict(reponses)
                elif not isinstance(reponses, dict):
                    try:
                        if isinstance(reponses, str):
                            reponses = json.loads(reponses)
                    except:
                        continue
                
                if not isinstance(reponses, dict):
                    continue
                
                questionnaires_utilises.append({
                    "id": questionnaire.id,
                    "type": questionnaire.type_questionnaire
                })
                
                # Extraire selon le type de questionnaire
                if questionnaire.type_questionnaire == "administratif":
                    # Informations personnelles
                    personal = reponses.get("personal", {})
                    if personal:
                        infos_personnelles.update({
                            "nom": personal.get("fullName", "").split()[-1] if personal.get("fullName") else "",
                            "prenom": personal.get("fullName", "").split()[0] if personal.get("fullName") else "",
                            "date_naissance": personal.get("birthDate", ""),
                            "sexe": personal.get("gender", ""),
                            "telephone": personal.get("phone", ""),
                            "email": personal.get("email", ""),
                            "adresse": personal.get("address", ""),
                            "pays": personal.get("nationality", ""),
                            "numero_passeport": personal.get("passportNumber", ""),
                            "date_expiration_passeport": personal.get("passportExpiryDate", "")
                        })
                    
                    # Informations voyage (si disponibles dans administratif)
                    technical = reponses.get("technical", {})
                    if technical:
                        infos_voyage.update({
                            "destination": technical.get("destination", ""),
                            "date_depart": technical.get("dateDepart", ""),
                            "date_retour": technical.get("dateRetour", ""),
                            "duree_sejour": technical.get("dureeSejour", "")
                        })
                
                elif questionnaire.type_questionnaire == "medical":
                    # Informations santé
                    medical = reponses.get("medical", {})
                    if medical:
                        infos_sante.update({
                            "historique_medical": medical.get("historiqueMedical", {}),
                            "sante_actuelle": medical.get("santeActuelle", {}),
                            "mode_vie": medical.get("modeVie", {}),
                            "allergies": medical.get("allergies", {}),
                            "sante_mentale": medical.get("santeMentale", {})
                        })
                
                # Si le questionnaire contient des infos personnelles directement
                if "fullName" in reponses or "nom" in reponses:
                    infos_personnelles.update({
                        "nom": reponses.get("nom") or (reponses.get("fullName", "").split()[-1] if reponses.get("fullName") else ""),
                        "prenom": reponses.get("prenom") or (reponses.get("fullName", "").split()[0] if reponses.get("fullName") else ""),
                        "email": reponses.get("email", ""),
                        "telephone": reponses.get("telephone", ""),
                        "date_naissance": reponses.get("date_naissance") or reponses.get("birthDate", "")
                    })
            
            logger.info(f"📋 Données extraites: {len(infos_personnelles)} champs personnels, {len(infos_sante)} champs santé")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des données des questionnaires: {e}", exc_info=True)
        
        return {
            "infos_personnelles": infos_personnelles,
            "infos_sante": infos_sante,
            "infos_voyage": infos_voyage,
            "questionnaires": questionnaires_utilises
        }
    
    @staticmethod
    def trigger_ia_analysis(
        db: Session,
        souscription: Souscription,
        background: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Déclenche automatiquement l'analyse IA pour une souscription
        
        Args:
            db: Session SQLAlchemy
            souscription: La souscription à analyser
            background: Si True, l'analyse se fait en arrière-plan (non bloquant)
        
        Returns:
            Résultat de l'analyse ou None si en arrière-plan
        """
        try:
            # Collecter les documents
            logger.info(f"🔍 Collecte des documents pour souscription {souscription.id}")
            documents = IAAutoService.collect_subscription_documents(db, souscription)
            
            if not documents:
                logger.warning(f"⚠️ Aucun document trouvé pour souscription {souscription.id}")
                return None
            
            logger.info(f"📄 {len(documents)} document(s) collecté(s) pour l'analyse IA")
            
            # Générer un demande_id
            demande_id = f"DEM-{souscription.numero_souscription}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            # Analyser chaque document
            resultats_analyse = []
            fichiers_temp = []
            
            try:
                for doc_info in documents:
                    try:
                        resultat = analyser_document(doc_info['path'])
                        resultats_analyse.append({
                            "status": resultat.get("status", "ok"),
                            "nom_fichier": doc_info['original_name'],
                            "analyse": resultat
                        })
                        fichiers_temp.append(doc_info['path'])
                    except Exception as e:
                        logger.error(f"Erreur lors de l'analyse du document {doc_info['original_name']}: {e}")
                        resultats_analyse.append({
                            "status": "error",
                            "nom_fichier": doc_info['original_name'],
                            "erreur": str(e)
                        })
                        fichiers_temp.append(doc_info['path'])
                
                # Extraire les informations depuis les questionnaires (JSON, pas besoin d'OCR)
                infos_questionnaires = IAAutoService._extract_questionnaire_data(db, souscription)
                logger.info(f"📋 Informations extraites depuis {len(infos_questionnaires.get('questionnaires', []))} questionnaire(s)")
                
                # Enrichir les résultats d'analyse avec les données des questionnaires
                if infos_questionnaires.get("infos_personnelles"):
                    # Fusionner les infos personnelles des questionnaires avec celles de l'OCR
                    for resultat in resultats_analyse:
                        if resultat.get("status") == "ok" and "analyse" in resultat:
                            analyse = resultat["analyse"]
                            # Priorité aux données OCR, compléter avec les questionnaires si manquant
                            infos_perso_ocr = analyse.get("infos_personnelles", {})
                            infos_perso_quest = infos_questionnaires.get("infos_personnelles", {})
                            
                            # Fusionner : OCR en priorité, questionnaires en complément
                            for key, value in infos_perso_quest.items():
                                if not infos_perso_ocr.get(key) or infos_perso_ocr.get(key) == "":
                                    infos_perso_ocr[key] = value
                            
                            analyse["infos_personnelles"] = infos_perso_ocr
                            
                            # Ajouter aussi les infos santé du questionnaire médical
                            if infos_questionnaires.get("infos_sante"):
                                analyse["infos_sante"] = infos_questionnaires.get("infos_sante")
                            
                            # Ajouter les infos voyage si disponibles
                            if infos_questionnaires.get("infos_voyage"):
                                analyse["infos_voyage"] = infos_questionnaires.get("infos_voyage")
                
                # Formater pour l'Agent de Production
                resultat_final = formater_pour_agent_production(
                    resultats_analyse=resultats_analyse,
                    demande_id=demande_id
                )
                
                # Enrichir le résultat final avec les données des questionnaires
                if infos_questionnaires.get("infos_personnelles"):
                    infos_perso_final = resultat_final.get("infos_personnelles", {})
                    for key, value in infos_questionnaires.get("infos_personnelles", {}).items():
                        if not infos_perso_final.get(key) or infos_perso_final.get(key) == "N/A":
                            infos_perso_final[key] = value
                    resultat_final["infos_personnelles"] = infos_perso_final
                
                # Ajouter les résultats bruts pour la sauvegarde
                resultat_final["resultats_analyse_bruts"] = resultats_analyse
                
                # Déterminer les assureurs concernés
                infos_perso = resultat_final.get("infos_personnelles", {})
                infos_voyage = resultat_final.get("infos_voyage", {}) or infos_questionnaires.get("infos_voyage", {})
                
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
                
                # Récupérer les IDs des questionnaires
                questionnaires = db.query(Questionnaire).filter(
                    Questionnaire.souscription_id == souscription.id
                ).all()
                questionnaire_id = questionnaires[0].id if questionnaires else None
                
                # Sauvegarder l'analyse
                storage_analyses.sauvegarder_analyse(
                    demande_id=demande_id,
                    assureurs_concernes=assureurs_concernes,
                    resultat_complet=resultat_final,
                    db=db,
                    souscription_id=souscription.id,
                    questionnaire_id=questionnaire_id
                )
                
                logger.info(f"✅ Analyse IA sauvegardée pour souscription {souscription.id} (demande_id: {demande_id})")
                
                # Notifier l'Agent de Production
                IAAutoService._notify_production_agents(db, souscription, demande_id)
                
                return resultat_final
                
            finally:
                # Nettoyer les fichiers temporaires
                for file_path in fichiers_temp:
                    try:
                        if os.path.exists(file_path):
                            os.unlink(file_path)
                    except Exception as e:
                        logger.warning(f"Impossible de supprimer le fichier temporaire {file_path}: {e}")
        
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'analyse IA automatique pour souscription {souscription.id}: {e}", exc_info=True)
            return None
    
    @staticmethod
    def _notify_production_agents(
        db: Session,
        souscription: Souscription,
        demande_id: str
    ):
        """Notifie les agents de production que le rapport IA est prêt"""
        try:
            from app.models.user import User
            agents = db.query(User).filter(
                User.role == Role.PRODUCTION_AGENT,
                User.is_active == True
            ).all()
            
            for agent in agents:
                try:
                    NotificationService.create_notification(
                        user_id=agent.id,
                        type_notification="ia_analysis_ready",
                        titre="Rapport IA disponible",
                        message=(
                            f"Le rapport d'analyse IA pour la souscription #{souscription.numero_souscription} "
                            f"est maintenant disponible (demande_id: {demande_id})."
                        ),
                        lien_relation_id=souscription.id,
                        lien_relation_type="souscription",
                        channels=["email", "push"]
                    )
                except Exception as notif_error:
                    logger.warning(f"Erreur lors de la notification de l'agent {agent.id}: {notif_error}")
            
            logger.info(f"📧 {len(agents)} agent(s) de production notifié(s) pour le rapport IA de souscription {souscription.id}")
        
        except Exception as e:
            logger.error(f"Erreur lors de la notification des agents de production: {e}", exc_info=True)

