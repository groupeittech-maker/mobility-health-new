"""
═══════════════════════════════════════════════════════════════════════════════
ANALYSEUR DE DEMANDE DE SOUSCRIPTION
═══════════════════════════════════════════════════════════════════════════════

Ce module gère le flux réel d'une application de souscription :
1. Données saisies par l'utilisateur dans un formulaire (web/mobile)
2. Documents uploadés (CNI, passeport, attestations)
3. Comparaison et détection d'incohérences entre les deux

FLUX TYPIQUE:
─────────────
1. L'utilisateur remplit le formulaire sur l'app (infos perso + questionnaire médical)
2. L'utilisateur uploade ses documents (pièce d'identité, etc.)
3. Le backend envoie les données du formulaire + les fichiers au module IA
4. Le module analyse les documents ET compare avec les données saisies
5. Le module retourne les scores + les incohérences détectées

═══════════════════════════════════════════════════════════════════════════════
"""

import os
import tempfile
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from .analyse import analyser_document
from .formateur import formater_resultat, ROLE_ASSUREUR, ROLE_MEDECIN_MH

logger = logging.getLogger(__name__)


class AnalyseurDemande:
    """
    Analyseur complet de demande de souscription
    
    Gère à la fois :
    - Les données saisies dans le formulaire (JSON)
    - Les documents uploadés (PDF, images)
    - La comparaison entre les deux
    """
    
    def __init__(self):
        self.demande_id = None
        self.donnees_formulaire = {}
        self.documents_analyses = []
        self.incoherences_detectees = []
    
    def analyser_demande_complete(
        self,
        donnees_formulaire: Dict[str, Any],
        fichiers_uploades: List[str] = None,
        fichiers_bytes: List[tuple] = None,
        demande_id: str = None
    ) -> Dict:
        """
        Analyse une demande complète de souscription
        
        Args:
            donnees_formulaire: Données saisies par l'utilisateur dans le formulaire
                {
                    "infos_personnelles": {
                        "nom": "DUPONT",
                        "prenom": "Jean",
                        "date_naissance": "15/03/1985",
                        "sexe": "M",
                        "email": "jean.dupont@email.com",
                        "telephone": "+33612345678",
                        ...
                    },
                    "questionnaire_medical": {
                        "hypertension": False,
                        "diabete": False,
                        "fumeur": False,
                        "alcool": "occasionnel",
                        ...
                    },
                    "infos_voyage": {
                        "destination": "Europe",
                        "frequence": "2 fois par an",
                        ...
                    }
                }
            
            fichiers_uploades: Liste des chemins vers les fichiers uploadés
                ["uploads/cni.pdf", "uploads/passeport.jpg"]
            
            fichiers_bytes: Alternative - Liste de tuples (nom_fichier, contenu_bytes)
                [("cni.pdf", b"..."), ("passeport.jpg", b"...")]
            
            demande_id: ID optionnel de la demande
        
        Returns:
            Résultat complet de l'analyse avec comparaison
        """
        self.demande_id = demande_id or f"DEM-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.donnees_formulaire = donnees_formulaire
        self.documents_analyses = []
        self.incoherences_detectees = []
        
        logger.info(f"📋 Analyse de la demande {self.demande_id}")
        
        # ═══════════════════════════════════════════════════════════════
        # ÉTAPE 1: Analyser les documents uploadés (si fournis)
        # ═══════════════════════════════════════════════════════════════
        
        if fichiers_uploades:
            self._analyser_fichiers_depuis_chemins(fichiers_uploades)
        elif fichiers_bytes:
            self._analyser_fichiers_depuis_bytes(fichiers_bytes)
        
        # ═══════════════════════════════════════════════════════════════
        # ÉTAPE 2: Comparer les données formulaire avec les documents
        # ═══════════════════════════════════════════════════════════════
        
        self._comparer_donnees()
        
        # ═══════════════════════════════════════════════════════════════
        # ÉTAPE 3: Calculer les scores globaux
        # ═══════════════════════════════════════════════════════════════
        
        scores = self._calculer_scores_globaux()
        
        # ═══════════════════════════════════════════════════════════════
        # ÉTAPE 4: Construire le résultat
        # ═══════════════════════════════════════════════════════════════
        
        resultat = {
            "demande_id": self.demande_id,
            "date_analyse": datetime.now().isoformat(),
            "source_donnees": {
                "formulaire": bool(donnees_formulaire),
                "documents_uploades": len(self.documents_analyses)
            },
            "donnees_formulaire": self._formater_donnees_formulaire(),
            "documents_analyses": self.documents_analyses,
            "comparaison": {
                "incoherences_detectees": self.incoherences_detectees,
                "nb_incoherences": len(self.incoherences_detectees),
                "donnees_coherentes": len(self.incoherences_detectees) == 0
            },
            "scores": scores,
            "evaluation": self._generer_evaluation(scores),
            "status": "ok"
        }
        
        logger.info(f"✅ Analyse terminée - {len(self.incoherences_detectees)} incohérence(s) détectée(s)")
        
        return resultat
    
    def _analyser_fichiers_depuis_chemins(self, chemins: List[str]):
        """Analyse les fichiers depuis leurs chemins"""
        infos_reference = None
        
        for chemin in chemins:
            if os.path.exists(chemin):
                logger.info(f"📄 Analyse du fichier: {chemin}")
                
                resultat = analyser_document(chemin, infos_client_reference=infos_reference)
                
                if resultat.get("status") == "ok":
                    if infos_reference is None:
                        infos_reference = resultat.get("infos_personnelles")
                    
                    self.documents_analyses.append({
                        "nom_fichier": os.path.basename(chemin),
                        "analyse": resultat,
                        "status": "ok"
                    })
                else:
                    self.documents_analyses.append({
                        "nom_fichier": os.path.basename(chemin),
                        "erreur": resultat.get("message"),
                        "status": "erreur"
                    })
            else:
                logger.warning(f"⚠️ Fichier non trouvé: {chemin}")
    
    def _analyser_fichiers_depuis_bytes(self, fichiers: List[tuple]):
        """Analyse les fichiers depuis leur contenu binaire (upload web/mobile)"""
        infos_reference = None
        
        for nom_fichier, contenu in fichiers:
            logger.info(f"📄 Analyse du fichier uploadé: {nom_fichier}")
            
            # Sauvegarder temporairement
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{nom_fichier}") as tmp:
                tmp.write(contenu)
                tmp_path = tmp.name
            
            try:
                resultat = analyser_document(tmp_path, infos_client_reference=infos_reference)
                
                if resultat.get("status") == "ok":
                    if infos_reference is None:
                        infos_reference = resultat.get("infos_personnelles")
                    
                    self.documents_analyses.append({
                        "nom_fichier": nom_fichier,
                        "analyse": resultat,
                        "status": "ok"
                    })
                else:
                    self.documents_analyses.append({
                        "nom_fichier": nom_fichier,
                        "erreur": resultat.get("message"),
                        "status": "erreur"
                    })
            finally:
                # Nettoyer le fichier temporaire
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
    
    def _comparer_donnees(self):
        """Compare les données du formulaire avec celles extraites des documents"""
        
        infos_formulaire = self.donnees_formulaire.get("infos_personnelles", {})
        
        # Parcourir les documents analysés
        for doc in self.documents_analyses:
            if doc.get("status") != "ok":
                continue
            
            infos_document = doc.get("analyse", {}).get("infos_personnelles", {})
            nom_fichier = doc.get("nom_fichier", "Document")
            
            # ═══════════════════════════════════════════════════════════
            # Comparer le NOM
            # ═══════════════════════════════════════════════════════════
            nom_formulaire = infos_formulaire.get("nom", "").strip().upper()
            nom_document = infos_document.get("nom", "").strip().upper()
            
            if nom_formulaire and nom_document and nom_formulaire != nom_document:
                self.incoherences_detectees.append({
                    "type": "NOM_DIFFERENT",
                    "gravite": "CRITIQUE",
                    "message": f"🚨 FRAUDE SUSPECTÉE: Nom différent - Formulaire: '{nom_formulaire}', Document ({nom_fichier}): '{nom_document}'",
                    "champ": "nom",
                    "valeur_formulaire": nom_formulaire,
                    "valeur_document": nom_document,
                    "document": nom_fichier
                })
            
            # ═══════════════════════════════════════════════════════════
            # Comparer le PRÉNOM
            # ═══════════════════════════════════════════════════════════
            prenom_formulaire = infos_formulaire.get("prenom", "").strip().upper()
            prenom_document = infos_document.get("prenom", "").strip().upper()
            
            if prenom_formulaire and prenom_document and prenom_formulaire != prenom_document:
                self.incoherences_detectees.append({
                    "type": "PRENOM_DIFFERENT",
                    "gravite": "CRITIQUE",
                    "message": f"🚨 FRAUDE SUSPECTÉE: Prénom différent - Formulaire: '{prenom_formulaire}', Document ({nom_fichier}): '{prenom_document}'",
                    "champ": "prenom",
                    "valeur_formulaire": prenom_formulaire,
                    "valeur_document": prenom_document,
                    "document": nom_fichier
                })
            
            # ═══════════════════════════════════════════════════════════
            # Comparer la DATE DE NAISSANCE
            # ═══════════════════════════════════════════════════════════
            ddn_formulaire = self._normaliser_date(infos_formulaire.get("date_naissance", ""))
            ddn_document = self._normaliser_date(infos_document.get("date_naissance", ""))
            
            if ddn_formulaire and ddn_document and ddn_formulaire != ddn_document:
                self.incoherences_detectees.append({
                    "type": "DATE_NAISSANCE_DIFFERENTE",
                    "gravite": "CRITIQUE",
                    "message": f"🚨 FRAUDE SUSPECTÉE: Date de naissance différente - Formulaire: '{ddn_formulaire}', Document ({nom_fichier}): '{ddn_document}'",
                    "champ": "date_naissance",
                    "valeur_formulaire": ddn_formulaire,
                    "valeur_document": ddn_document,
                    "document": nom_fichier
                })
            
            # ═══════════════════════════════════════════════════════════
            # Comparer le SEXE
            # ═══════════════════════════════════════════════════════════
            sexe_formulaire = self._normaliser_sexe(infos_formulaire.get("sexe", ""))
            sexe_document = self._normaliser_sexe(infos_document.get("sexe", ""))
            
            if sexe_formulaire and sexe_document and sexe_formulaire != sexe_document:
                self.incoherences_detectees.append({
                    "type": "SEXE_DIFFERENT",
                    "gravite": "CRITIQUE",
                    "message": f"🚨 FRAUDE SUSPECTÉE: Sexe différent - Formulaire: '{sexe_formulaire}', Document ({nom_fichier}): '{sexe_document}'",
                    "champ": "sexe",
                    "valeur_formulaire": sexe_formulaire,
                    "valeur_document": sexe_document,
                    "document": nom_fichier
                })
    
    def _normaliser_date(self, date_str: str) -> str:
        """Normalise une date pour comparaison"""
        if not date_str:
            return ""
        # Remplacer les séparateurs
        date_str = date_str.replace("-", "/").replace(".", "/")
        return date_str.strip()
    
    def _normaliser_sexe(self, sexe: str) -> str:
        """Normalise le sexe pour comparaison"""
        if not sexe:
            return ""
        sexe = sexe.strip().upper()
        if sexe in ["M", "MASCULIN", "HOMME", "H", "MALE"]:
            return "M"
        elif sexe in ["F", "FÉMININ", "FEMININ", "FEMME", "FEMALE"]:
            return "F"
        return sexe
    
    def _calculer_scores_globaux(self) -> Dict:
        """Calcule les scores globaux de la demande"""
        
        # Scores de base depuis les documents
        scores_documents = []
        for doc in self.documents_analyses:
            if doc.get("status") == "ok" and "analyse" in doc:
                scores_documents.append(doc["analyse"].get("scores", {}))
        
        # Moyennes des scores des documents
        if scores_documents:
            prob_acceptation = sum(s.get("probabilite_acceptation", 0) for s in scores_documents) / len(scores_documents)
            prob_fraude = sum(s.get("probabilite_fraude", 0) for s in scores_documents) / len(scores_documents)
            score_coherence = sum(s.get("score_coherence", 0) for s in scores_documents) / len(scores_documents)
            score_risque = sum(s.get("score_risque", 0) for s in scores_documents) / len(scores_documents)
        else:
            # Si pas de documents, scores basés uniquement sur le questionnaire
            prob_acceptation = 0.7  # Valeur par défaut
            prob_fraude = 0.1
            score_coherence = 80.0
            score_risque = 0.2
        
        # ═══════════════════════════════════════════════════════════════
        # Ajuster les scores selon les incohérences détectées
        # ═══════════════════════════════════════════════════════════════
        
        nb_incoherences_critiques = sum(
            1 for inc in self.incoherences_detectees 
            if inc.get("gravite") == "CRITIQUE"
        )
        
        if nb_incoherences_critiques > 0:
            # Incohérences critiques = fraude suspectée
            prob_fraude = min(1.0, prob_fraude + (nb_incoherences_critiques * 0.3))
            prob_acceptation = max(0.0, prob_acceptation - (nb_incoherences_critiques * 0.2))
            score_coherence = max(0.0, score_coherence - (nb_incoherences_critiques * 20))
        
        # Calculer score de confiance assureur
        prob_confiance = (prob_acceptation * 0.4) + ((score_coherence / 100) * 0.3) + ((1 - prob_fraude) * 0.3)
        
        return {
            "probabilite_acceptation": round(prob_acceptation, 3),
            "probabilite_fraude": round(prob_fraude, 3),
            "probabilite_confiance_assureur": round(prob_confiance, 3),
            "score_coherence": round(score_coherence, 1),
            "score_risque": round(score_risque, 3)
        }
    
    def _generer_evaluation(self, scores: Dict) -> Dict:
        """Génère l'évaluation finale"""
        
        prob_fraude = scores.get("probabilite_fraude", 0)
        prob_acceptation = scores.get("probabilite_acceptation", 0)
        
        # Déterminer l'avis
        if prob_fraude >= 0.5:
            avis = "REJET RECOMMANDÉ (FRAUDE SUSPECTÉE)"
            decision = "REJETER"
        elif prob_acceptation >= 0.7 and prob_fraude < 0.3:
            avis = "FAVORABLE"
            decision = "ACCEPTER"
        elif prob_acceptation >= 0.5:
            avis = "RÉSERVÉ"
            decision = "ACCEPTER SOUS CONDITIONS"
        else:
            avis = "DÉFAVORABLE"
            decision = "REJETER"
        
        # Niveau de risque
        score_risque = scores.get("score_risque", 0)
        if score_risque >= 0.7:
            niveau_risque = "Très élevé"
        elif score_risque >= 0.5:
            niveau_risque = "Élevé"
        elif score_risque >= 0.3:
            niveau_risque = "Modéré"
        else:
            niveau_risque = "Faible"
        
        # Recommandations
        recommandations = []
        if self.incoherences_detectees:
            recommandations.append("⚠️ Vérification des documents originaux OBLIGATOIRE")
            recommandations.append("Les informations du formulaire ne correspondent pas aux documents")
        
        if prob_fraude >= 0.5:
            recommandations.append("⛔ Investigation approfondie recommandée")
        elif prob_acceptation < 0.5:
            recommandations.append("Examen médical complémentaire recommandé")
        else:
            recommandations.append("Traitement standard")
        
        return {
            "avis": avis,
            "decision_recommandee": decision,
            "niveau_risque": niveau_risque,
            "recommandations": recommandations,
            "alerte_fraude": prob_fraude >= 0.5,
            "nb_incoherences": len(self.incoherences_detectees)
        }
    
    def _formater_donnees_formulaire(self) -> Dict:
        """Formate les données du formulaire pour le résultat"""
        return {
            "infos_personnelles": self.donnees_formulaire.get("infos_personnelles", {}),
            "questionnaire_medical": self.donnees_formulaire.get("questionnaire_medical", {}),
            "infos_voyage": self.donnees_formulaire.get("infos_voyage", {})
        }
    
    def obtenir_vue_assureur(self) -> Dict:
        """Retourne la vue formatée pour l'assureur"""
        return formater_resultat(self.documents_analyses, role=ROLE_ASSUREUR, demande_id=self.demande_id)
    
    def obtenir_vue_medecin(self) -> Dict:
        """Retourne la vue formatée pour le médecin MH"""
        return formater_resultat(self.documents_analyses, role=ROLE_MEDECIN_MH, demande_id=self.demande_id)


# ═══════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════

def analyser_demande(
    donnees_formulaire: Dict,
    fichiers_uploades: List[str] = None,
    fichiers_bytes: List[tuple] = None,
    demande_id: str = None
) -> Dict:
    """
    Fonction raccourcie pour analyser une demande complète
    
    Exemple d'utilisation dans un backend:
    
    ```python
    from ia_module import analyser_demande
    
    # Données reçues du formulaire (web/mobile)
    donnees = {
        "infos_personnelles": {
            "nom": "DUPONT",
            "prenom": "Jean",
            "date_naissance": "15/03/1985",
            "sexe": "M",
            "email": "jean@email.com"
        },
        "questionnaire_medical": {
            "hypertension": False,
            "diabete": False,
            "fumeur": False
        }
    }
    
    # Documents uploadés (chemins ou bytes)
    fichiers = ["uploads/cni.pdf", "uploads/passeport.jpg"]
    
    # OU avec bytes (upload direct)
    fichiers_bytes = [
        ("cni.pdf", contenu_cni),
        ("passeport.jpg", contenu_passeport)
    ]
    
    # Analyser
    resultat = analyser_demande(
        donnees_formulaire=donnees,
        fichiers_uploades=fichiers,  # OU fichiers_bytes=fichiers_bytes
        demande_id="DEM-12345"
    )
    
    # Vérifier les incohérences
    if resultat["comparaison"]["nb_incoherences"] > 0:
        print("⚠️ ATTENTION: Incohérences détectées!")
        for inc in resultat["comparaison"]["incoherences_detectees"]:
            print(f"  - {inc['message']}")
    ```
    """
    analyseur = AnalyseurDemande()
    return analyseur.analyser_demande_complete(
        donnees_formulaire=donnees_formulaire,
        fichiers_uploades=fichiers_uploades,
        fichiers_bytes=fichiers_bytes,
        demande_id=demande_id
    )


# Instance globale réutilisable
analyseur_demande = AnalyseurDemande()

