"""
Stockage des analyses pour que les assureurs puissent les consulter
Utilise maintenant une base de données PostgreSQL via SQLAlchemy
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from decimal import Decimal

from app.models.ia_analysis import IAAnalysis, IAAnalysisAssureur, IAAnalysisDocument

logger = logging.getLogger(__name__)


class StorageAnalyses:
    """
    Stocke les analyses pour consultation par les assureurs
    Utilise une base de données PostgreSQL
    """
    
    def __init__(self, db: Optional[Session] = None):
        """
        Initialise le stockage
        
        Args:
            db: Session SQLAlchemy (optionnel, peut être passé lors des appels)
        """
        self.db = db
    
    def _get_db(self, db: Optional[Session] = None) -> Session:
        """Récupère la session DB (soit passée en paramètre, soit celle de l'instance)"""
        if db is not None:
            return db
        if self.db is not None:
            return self.db
        raise ValueError("Session DB requise. Passez 'db' en paramètre ou initialisez StorageAnalyses avec db=session")
    
    def sauvegarder_analyse(
        self,
        demande_id: str,
        assureurs_concernes: List[Dict],
        resultat_complet: Dict,
        db: Optional[Session] = None,
        souscription_id: Optional[int] = None,
        questionnaire_id: Optional[int] = None
    ):
        """
        Sauvegarde une analyse dans la base de données
        
        Args:
            demande_id: ID unique de la demande
            assureurs_concernes: Liste des assureurs concernés [{"id": 1, "nom": "..."}, ...]
            resultat_complet: Résultat complet de l'analyse
            db: Session SQLAlchemy
            souscription_id: ID de la souscription associée (optionnel)
            questionnaire_id: ID du questionnaire associé (optionnel)
        """
        db_session = self._get_db(db)
        
        try:
            # Extraire les informations essentielles
            infos_perso = resultat_complet.get("infos_personnelles", {})
            infos_sante = resultat_complet.get("infos_sante", {})
            infos_voyage = resultat_complet.get("infos_voyage", {})
            
            # Extraire les scores depuis scores_ia_detailles (format agent_production)
            scores_ia_detailles = resultat_complet.get("scores_ia_detailles", {})
            if scores_ia_detailles:
                # Les scores bruts sont dans les clés *_brut (valeurs entre 0-1)
                prob_acceptation_brut = scores_ia_detailles.get("probabilite_acceptation_brut", 0)
                prob_fraude_brut = scores_ia_detailles.get("probabilite_fraude_brut", 0)
                
                # score_confiance_assureur est en pourcentage string, extraire la valeur
                score_confiance_str = scores_ia_detailles.get("score_confiance_assureur", "0%")
                score_confiance_val = float(score_confiance_str.replace("%", "")) / 100 if isinstance(score_confiance_str, str) else score_confiance_str
                
                # score_coherence est au format "XX.X/100", extraire la valeur (déjà en 0-100)
                score_coherence_str = scores_ia_detailles.get("score_coherence", "0/100")
                score_coherence_val = float(score_coherence_str.split("/")[0]) if isinstance(score_coherence_str, str) and "/" in score_coherence_str else (float(score_coherence_str) if isinstance(score_coherence_str, (str, int, float)) else 0)
                
                scores = {
                    "probabilite_acceptation": prob_acceptation_brut,
                    "probabilite_fraude": prob_fraude_brut,
                    "probabilite_confiance_assureur": score_confiance_val,
                    "score_coherence": score_coherence_val,  # Déjà en 0-100
                    "score_risque": 0,  # À calculer si nécessaire
                    "score_confiance": 0,  # À calculer si nécessaire
                    "confiance_ocr": 0  # Sera calculé depuis les documents
                }
            else:
                # Fallback sur l'ancien format
                scores = resultat_complet.get("scores", {})
            
            # Extraire l'évaluation depuis resume_executif ou evaluation
            resume_executif = resultat_complet.get("resume_executif", {})
            evaluation_raw = resultat_complet.get("evaluation", {})
            
            # Construire l'évaluation complète
            evaluation = {
                "avis": resume_executif.get("decision_ia") or evaluation_raw.get("avis", "N/A"),
                "niveau_risque": evaluation_raw.get("niveau_risque", "N/A"),
                "niveau_fraude": evaluation_raw.get("niveau_fraude", "N/A"),
                "niveau_confiance_assureur": evaluation_raw.get("niveau_confiance_assureur", "N/A"),
                "facteurs_risque": resultat_complet.get("problemes_detectes", {}).get("incoherences", {}).get("liste_detaillee", []) or evaluation_raw.get("facteurs_risque", []),
                "signaux_fraude": resultat_complet.get("problemes_detectes", {}).get("signaux_fraude", {}).get("liste_detaillee", []) or evaluation_raw.get("signaux_fraude", []),
                "incoherences": resultat_complet.get("problemes_detectes", {}).get("incoherences", {}).get("liste_detaillee", []) or evaluation_raw.get("incoherences", []),
                "message_assureur": resume_executif.get("motif_decision") or evaluation_raw.get("message_ia", ""),
                "commentaire": resume_executif.get("motif_decision", "")
            }
            
            verification_doc = resultat_complet.get("verification_document", {})
            
            # Extraire les documents analysés
            # Priorité 1: Utiliser les résultats bruts si disponibles (format attendu)
            resultats_bruts = resultat_complet.get("resultats_analyse_bruts", [])
            if resultats_bruts:
                documents_analyses = resultats_bruts
            else:
                # Priorité 2: Chercher dans verification_documents
                verification_docs = resultat_complet.get("verification_documents", {})
                documents_analyses = verification_docs.get("documents_analyses", [])
                # Priorité 3: Chercher à la racine
                if not documents_analyses:
                    documents_analyses = resultat_complet.get("documents_analyses", [])
                # Priorité 4: Chercher dans analyse_par_document
                if not documents_analyses:
                    documents_analyses = resultat_complet.get("analyse_par_document", [])
            
            # Vérifier si l'analyse existe déjà
            analyse_existante = db_session.query(IAAnalysis).filter(
                IAAnalysis.demande_id == demande_id
            ).first()
            
            if analyse_existante:
                # Mettre à jour l'analyse existante
                analyse = analyse_existante
                logger.info(f"🔄 Mise à jour de l'analyse existante {demande_id}")
            else:
                # Créer une nouvelle analyse
                analyse = IAAnalysis(demande_id=demande_id)
                db_session.add(analyse)
                logger.info(f"✅ Création d'une nouvelle analyse {demande_id}")
            
            # Mettre à jour les champs
            analyse.souscription_id = souscription_id
            analyse.questionnaire_id = questionnaire_id
            analyse.client_nom = infos_perso.get("nom", "") or "N/A"
            analyse.client_prenom = infos_perso.get("prenom", "") or "N/A"
            analyse.client_pays = infos_perso.get("pays", "")
            analyse.client_email = infos_perso.get("email", "")
            
            # Scores
            analyse.probabilite_acceptation = Decimal(str(scores.get("probabilite_acceptation", 0)))
            analyse.probabilite_fraude = Decimal(str(scores.get("probabilite_fraude", 0)))
            analyse.probabilite_confiance_assureur = Decimal(str(scores.get("probabilite_confiance_assureur", 0)))
            analyse.score_coherence = Decimal(str(scores.get("score_coherence", 0)))
            analyse.score_risque = Decimal(str(scores.get("score_risque", 0)))
            analyse.score_confiance = Decimal(str(scores.get("score_confiance", 0)))
            
            # Évaluation
            analyse.avis = evaluation.get("avis", "N/A")
            analyse.niveau_risque = evaluation.get("niveau_risque", "N/A")
            analyse.niveau_fraude = evaluation.get("niveau_fraude", "N/A")
            analyse.niveau_confiance_assureur = evaluation.get("niveau_confiance_assureur", "N/A")
            
            # Données JSON
            analyse.facteurs_risque = evaluation.get("facteurs_risque", [])
            analyse.signaux_fraude = evaluation.get("signaux_fraude", [])
            analyse.incoherences = evaluation.get("incoherences", [])
            analyse.infos_personnelles = infos_perso
            analyse.infos_sante = infos_sante
            analyse.infos_voyage = infos_voyage
            analyse.resultat_complet = resultat_complet
            
            # Métadonnées
            analyse.date_analyse = datetime.now()
            
            # Calculer la confiance OCR moyenne depuis les documents
            confiances_ocr = []
            for doc in documents_analyses:
                if isinstance(doc, dict):
                    confiance = doc.get("confiance_ocr") or doc.get("analyse", {}).get("confiance_ocr")
                    if confiance is not None:
                        # Si c'est déjà en pourcentage (> 1), garder tel quel, sinon multiplier par 100
                        confiance_val = float(confiance) if float(confiance) > 1 else float(confiance) * 100
                        confiances_ocr.append(confiance_val)
            
            if confiances_ocr:
                confiance_ocr_moyenne = sum(confiances_ocr) / len(confiances_ocr)
                analyse.confiance_ocr = Decimal(str(confiance_ocr_moyenne))
            else:
                analyse.confiance_ocr = scores.get("confiance_ocr") if scores.get("confiance_ocr") else None
            
            analyse.nb_documents_analyses = len(documents_analyses)
            
            # Commentaire et message
            analyse.commentaire = evaluation.get("commentaire", "")
            analyse.message_ia = evaluation.get("message_assureur", "")
            
            db_session.flush()  # Pour obtenir l'ID
            
            # Sauvegarder les documents analysés
            if documents_analyses:
                # Supprimer les anciens documents
                db_session.query(IAAnalysisDocument).filter(
                    IAAnalysisDocument.analyse_id == analyse.id
                ).delete()
                
                for doc_data in documents_analyses:
                    if doc_data.get("status") == "ok" and "analyse" in doc_data:
                        doc_analyse = doc_data["analyse"]
                        doc_verif = doc_analyse.get("verification_document", {})
                        
                        # Convertir les valeurs booléennes (peuvent être des strings)
                        def to_bool(val, default=False):
                            if isinstance(val, bool):
                                return val
                            if isinstance(val, str):
                                return val.lower() in ("true", "1", "yes", "oui")
                            return bool(val) if val is not None else default
                        
                        # Sauvegarder le texte extrait (même s'il est vide, on sauvegarde une chaîne vide)
                        texte_extrait_val = doc_analyse.get("texte_extrait")
                        if texte_extrait_val is not None:
                            texte_extrait = (texte_extrait_val[:5000] if texte_extrait_val else "")  # Limiter à 5000 caractères
                        else:
                            texte_extrait = None
                        
                        doc = IAAnalysisDocument(
                            analyse_id=analyse.id,
                            nom_fichier=doc_data.get("nom_fichier", "Document"),
                            type_document=doc_verif.get("type_document"),
                            type_fichier=doc_analyse.get("type_fichier"),
                            confiance_ocr=Decimal(str(doc_analyse.get("confiance_ocr", 0))) if doc_analyse.get("confiance_ocr") else None,
                            texte_extrait=texte_extrait,
                            est_expire=to_bool(doc_verif.get("est_expire"), False),
                            qualite_ok=to_bool(doc_verif.get("qualite_ok"), True),
                            est_complet=to_bool(doc_verif.get("est_complet"), True),
                            est_coherent=to_bool(doc_verif.get("est_coherent_documents"), True),
                            message_expiration=doc_verif.get("message_expiration"),
                            message_qualite=doc_verif.get("message_qualite"),
                            message_completude=doc_verif.get("message_completude"),
                            message_coherence=doc_verif.get("message_coherence"),
                            resultat_document=doc_analyse
                        )
                        db_session.add(doc)
            
            # Sauvegarder les liaisons avec les assureurs
            # Supprimer les anciennes liaisons
            db_session.query(IAAnalysisAssureur).filter(
                IAAnalysisAssureur.analyse_id == analyse.id
            ).delete()
            
            # Créer les nouvelles liaisons
            for assureur in assureurs_concernes:
                assureur_id = assureur.get("id")
                if assureur_id:
                    liaison = IAAnalysisAssureur(
                        analyse_id=analyse.id,
                        assureur_id=int(assureur_id),
                        notifie="pending"
                    )
                    db_session.add(liaison)
            
            db_session.commit()
            logger.info(f"✅ Analyse {demande_id} sauvegardée pour {len(assureurs_concernes)} assureur(s)")
            
        except Exception as e:
            db_session.rollback()
            logger.error(f"❌ Erreur lors de la sauvegarde de l'analyse {demande_id}: {e}")
            raise
    
    def get_analyses_par_assureur(
        self,
        assureur_id: int,
        status: Optional[str] = None,  # 'favorable', 'reserve', 'defavorable'
        limit: int = 50,
        db: Optional[Session] = None
    ) -> List[Dict]:
        """
        Récupère les analyses pour un assureur
        
        Args:
            assureur_id: ID de l'assureur
            status: Filtrer par avis ('favorable', 'reserve', 'defavorable')
            limit: Nombre maximum d'analyses à retourner
            db: Session SQLAlchemy
        
        Returns:
            Liste des analyses (format dict pour compatibilité)
        """
        db_session = self._get_db(db)
        
        query = db_session.query(IAAnalysis).join(
            IAAnalysisAssureur
        ).filter(
            IAAnalysisAssureur.assureur_id == assureur_id
        )
        
        # Filtrer par status si demandé
        if status:
            if status == "favorable":
                query = query.filter(IAAnalysis.avis.like("%FAVORABLE%"))
            elif status == "reserve":
                query = query.filter(or_(
                    IAAnalysis.avis.like("%RÉSERVÉ%"),
                    IAAnalysis.avis.like("%RESERVE%")
                ))
            elif status == "defavorable":
                query = query.filter(or_(
                    IAAnalysis.avis.like("%DÉFAVORABLE%"),
                    IAAnalysis.avis.like("%DEFAVORABLE%"),
                    IAAnalysis.avis.like("%REJET%")
                ))
        
        # Trier par date (plus récent en premier)
        query = query.order_by(IAAnalysis.date_analyse.desc())
        
        # Limiter
        analyses = query.limit(limit).all()
        
        # Convertir en format dict pour compatibilité
        return [self._analyse_to_dict(a) for a in analyses]
    
    def get_resume_assureur(self, assureur_id: int, db: Optional[Session] = None) -> Dict:
        """
        Calcule le résumé des statistiques pour un assureur
        
        Args:
            assureur_id: ID de l'assureur
            db: Session SQLAlchemy
        
        Returns:
            Dictionnaire avec les statistiques
        """
        db_session = self._get_db(db)
        
        # Requête de base
        query = db_session.query(IAAnalysis).join(
            IAAnalysisAssureur
        ).filter(
            IAAnalysisAssureur.assureur_id == assureur_id
        )
        
        # Statistiques globales
        total = query.count()
        
        # Analyses aujourd'hui
        aujourdhui = datetime.now().date()
        analyses_aujourdhui = query.filter(
            func.date(IAAnalysis.date_analyse) == aujourdhui
        ).count()
        
        # Moyennes des scores
        result = query.with_entities(
            func.avg(IAAnalysis.probabilite_acceptation).label('avg_acceptation'),
            func.avg(IAAnalysis.probabilite_fraude).label('avg_fraude')
        ).first()
        
        taux_acceptation_moyen = float(result.avg_acceptation * 100) if result.avg_acceptation else 0
        taux_fraude_moyen = float(result.avg_fraude * 100) if result.avg_fraude else 0
        
        # Compter par avis
        demandes_favorables = query.filter(IAAnalysis.avis.like("%FAVORABLE%")).count()
        demandes_reservees = query.filter(or_(
            IAAnalysis.avis.like("%RÉSERVÉ%"),
            IAAnalysis.avis.like("%RESERVE%")
        )).count()
        demandes_defavorables = query.filter(or_(
            IAAnalysis.avis.like("%DÉFAVORABLE%"),
            IAAnalysis.avis.like("%DEFAVORABLE%"),
            IAAnalysis.avis.like("%REJET%")
        )).count()
        
        return {
            "total_analyses": total,
            "analyses_aujourdhui": analyses_aujourdhui,
            "taux_acceptation_moyen": round(taux_acceptation_moyen, 2),
            "taux_fraude_moyen": round(taux_fraude_moyen, 2),
            "demandes_favorables": demandes_favorables,
            "demandes_reservees": demandes_reservees,
            "demandes_defavorables": demandes_defavorables,
            "demandes_en_attente": 0  # À implémenter si vous suivez les statuts
        }
    
    def get_analyse_details(self, demande_id: str, assureur_id: int, db: Optional[Session] = None) -> Optional[Dict]:
        """
        Récupère les détails complets d'une analyse pour un assureur
        
        Args:
            demande_id: ID de la demande
            assureur_id: ID de l'assureur (pour vérifier les permissions)
            db: Session SQLAlchemy
        
        Returns:
            Détails complets de l'analyse ou None
        """
        db_session = self._get_db(db)
        
        # Récupérer l'analyse
        analyse = db_session.query(IAAnalysis).filter(
            IAAnalysis.demande_id == demande_id
        ).first()
        
        if not analyse:
            return None
        
        # Vérifier que l'assureur est concerné
        liaison = db_session.query(IAAnalysisAssureur).filter(
            and_(
                IAAnalysisAssureur.analyse_id == analyse.id,
                IAAnalysisAssureur.assureur_id == assureur_id
            )
        ).first()
        
        if not liaison:
            return None
        
        # Retourner les détails complets
        return {
            "demande_id": demande_id,
            "client": {
                "nom": analyse.client_nom,
                "prenom": analyse.client_prenom,
                "pays": analyse.client_pays
            },
            "infos_personnelles": analyse.infos_personnelles or {},
            "infos_sante": analyse.infos_sante or {},
            "infos_voyage": analyse.infos_voyage or {},
            "scores": {
                "probabilite_acceptation": float(analyse.probabilite_acceptation),
                "probabilite_fraude": float(analyse.probabilite_fraude),
                "probabilite_confiance_assureur": float(analyse.probabilite_confiance_assureur),
                "score_coherence": float(analyse.score_coherence),
                "score_risque": float(analyse.score_risque)
            },
            "evaluation": {
                "avis": analyse.avis,
                "facteurs_risque": analyse.facteurs_risque or [],
                "signaux_fraude": analyse.signaux_fraude or [],
                "incoherences": analyse.incoherences or [],
                "message_ia": analyse.message_ia or ""
            },
            "date_analyse": analyse.date_analyse.isoformat()
        }
    
    def cleanup_old_analyses(self, max_age_days: int = 90, db: Optional[Session] = None):
        """
        Nettoie les anciennes analyses (pour libérer de l'espace)
        
        Args:
            max_age_days: Nombre de jours maximum de conservation
            db: Session SQLAlchemy
        """
        db_session = self._get_db(db)
        
        cutoff = datetime.now() - timedelta(days=max_age_days)
        
        # Supprimer les analyses anciennes (cascade supprimera aussi les liaisons et documents)
        deleted = db_session.query(IAAnalysis).filter(
            IAAnalysis.date_analyse < cutoff
        ).delete()
        
        db_session.commit()
        
        if deleted > 0:
            logger.info(f"🧹 {deleted} anciennes analyses nettoyées (plus de {max_age_days} jours)")
    
    def _analyse_to_dict(self, analyse: IAAnalysis) -> Dict:
        """Convertit un objet IAAnalysis en dictionnaire (pour compatibilité)"""
        return {
            "demande_id": analyse.demande_id,
            "assureurs_concernes": [
                {"id": lia.assureur_id, "nom": lia.assureur.nom if lia.assureur else "N/A"}
                for lia in analyse.assureurs_concernes
            ],
            "client_nom": analyse.client_nom,
            "client_prenom": analyse.client_prenom,
            "client_pays": analyse.client_pays,
            "scores": {
                "probabilite_acceptation": float(analyse.probabilite_acceptation),
                "probabilite_fraude": float(analyse.probabilite_fraude),
                "probabilite_confiance_assureur": float(analyse.probabilite_confiance_assureur),
                "score_coherence": float(analyse.score_coherence),
                "score_risque": float(analyse.score_risque)
            },
            "avis": analyse.avis,
            "facteurs_risque": analyse.facteurs_risque or [],
            "signaux_fraude": analyse.signaux_fraude or [],
            "incoherences": analyse.incoherences or [],
            "message_ia": analyse.message_ia or "",
            "date_analyse": analyse.date_analyse,
            "resultat_complet": analyse.resultat_complet or {}
        }


# Instance globale (sans DB par défaut, doit être initialisée avec db lors de l'utilisation)
storage_analyses = StorageAnalyses()
