"""
Module IA de Souscription - MH Assurances
==========================================

Ce module fournit les fonctionnalités d'analyse IA pour le traitement
des demandes de souscription d'assurance.

FONCTIONNALITÉS PRINCIPALES:
----------------------------
1. Analyse de documents (PDF, images) via OCR
2. Extraction d'informations personnelles et médicales
3. Calcul de scores de risque et de probabilités
4. Détection de fraude et incohérences
5. Formatage des résultats pour Assureur et Médecin MH

RESTRICTION D'ACCÈS:
--------------------
⚠️ Le questionnaire médical complet n'est accessible QUE par le Médecin MH
   L'assureur ne voit que les métriques de décision, pas les détails médicaux

UTILISATION:
------------
    from ia_module import analyser_document, formater_resultat
    
    # Analyser un document
    resultat = analyser_document("chemin/vers/document.pdf")
    
    # Formater pour l'assureur (sans questionnaire médical)
    vue_assureur = formater_resultat([{"nom_fichier": "doc.pdf", "analyse": resultat, "status": "ok"}], role="assureur")
    
    # Formater pour le médecin MH (avec questionnaire médical complet)
    vue_medecin = formater_resultat([{"nom_fichier": "doc.pdf", "analyse": resultat, "status": "ok"}], role="medecin_mh")

AUTEUR: Équipe IA MH Assurances
VERSION: 2.0.0
"""

# ═══════════════════════════════════════════════════════════════
# EXPORTS PRINCIPAUX
# ═══════════════════════════════════════════════════════════════

# Fonction principale d'analyse de documents
from .analyse import analyser_document

# Fonctions de formatage selon le rôle utilisateur
from .formateur import (
    formater_resultat,
    formater_pour_assureur,
    formater_pour_medecin_mh,
    formater_pour_agent_technique,
    formater_pour_agent_production,
    ROLE_ASSUREUR,
    ROLE_MEDECIN_MH,
    ROLE_AGENT_TECHNIQUE,
    ROLE_AGENT_PRODUCTION
)

# Analyseur de demande complète (formulaire + documents)
from .analyseur_demande import (
    analyser_demande,
    AnalyseurDemande,
    analyseur_demande
)

# Routeur d'assureurs (optionnel - pour routage automatique)
from .router_assureur import RouterAssureur, router_assureur

# Stockage des analyses (optionnel - pour mise en cache)
from .storage_analyses import StorageAnalyses, storage_analyses

# Configuration (détection automatique local/production)
from .config import config, get_tesseract_cmd, get_poppler_path, is_production

# ═══════════════════════════════════════════════════════════════
# FONCTION SIMPLIFIÉE POUR AGENT DE PRODUCTION
# ═══════════════════════════════════════════════════════════════

def analyser_pour_agent_production(fichiers: list, demande_id: str = None) -> dict:
    """
    🎯 Fonction principale - Analyse les documents et retourne le résultat 
    formaté UNIQUEMENT pour l'Agent de Production.
    
    Args:
        fichiers: Liste des chemins de fichiers à analyser
        demande_id: ID optionnel de la demande
    
    Returns:
        Résultat complet formaté pour l'Agent de Production avec:
        - Résumé exécutif avec décision IA
        - Score global d'acceptation
        - Problèmes détectés (incohérences, fraude)
        - Actions requises
        - Questionnaire médical
        - Statuts des validations
    
    Exemple:
        from ia_module import analyser_pour_agent_production
        
        fichiers = ["questionnaire.pdf", "cni.png"]
        resultat = analyser_pour_agent_production(fichiers, demande_id="DEM-001")
        
        # Accéder à la décision
        print(resultat["resume_executif"]["decision_ia"])
    """
    resultats = []
    infos_reference = None
    
    for filepath in fichiers:
        resultat = analyser_document(filepath, infos_reference)
        
        if resultat.get("status") == "ok":
            # Garder les infos du premier document comme référence
            if infos_reference is None:
                infos_reference = resultat.get("infos_personnelles", {})
        
        # Extraire le nom du fichier
        nom_fichier = filepath.replace("\\", "/").split("/")[-1]
        
        resultats.append({
            "nom_fichier": nom_fichier,
            "status": resultat.get("status", "erreur"),
            "analyse": resultat if resultat.get("status") == "ok" else None,
            "erreur": resultat.get("erreur") if resultat.get("status") != "ok" else None
        })
    
    return formater_pour_agent_production(resultats, demande_id)


# ═══════════════════════════════════════════════════════════════
# INFORMATIONS DU MODULE
# ═══════════════════════════════════════════════════════════════

__version__ = "2.1.0"
__author__ = "Équipe IA MH Assurances"

__all__ = [
    # 🎯 FONCTION PRINCIPALE - Agent de Production
    "analyser_pour_agent_production",
    
    # Fonctions de base
    "analyser_document",
    "formater_resultat",
    "formater_pour_agent_production",
    
    # Constantes de rôles
    "ROLE_AGENT_PRODUCTION",
    
    # Autres fonctions (si besoin)
    "formater_pour_assureur",
    "formater_pour_medecin_mh",
    "formater_pour_agent_technique",
    "ROLE_ASSUREUR",
    "ROLE_MEDECIN_MH",
    "ROLE_AGENT_TECHNIQUE",
    
    # Analyseur de demande complète
    "analyser_demande",
    "AnalyseurDemande",
    "analyseur_demande",
    
    # Classes optionnelles
    "RouterAssureur",
    "router_assureur",
    "StorageAnalyses", 
    "storage_analyses",
]
