"""
Module de formatage des résultats d'analyse
Formate les données différemment selon le type d'utilisateur (Assureur ou Médecin MH)

IMPORTANT: Le questionnaire médical complet n'est accessible QUE par le Médecin MH
"""

from datetime import datetime
from typing import Dict, List, Optional, Literal

# Types de rôles utilisateurs
ROLE_ASSUREUR = "assureur"
ROLE_MEDECIN_MH = "medecin_mh"
ROLE_AGENT_TECHNIQUE = "agent_technique"
ROLE_AGENT_PRODUCTION = "agent_production"


def formater_resultat(
    resultats_analyse: List[Dict],
    role: Literal["assureur", "medecin_mh", "agent_technique", "agent_production"],
    demande_id: Optional[str] = None,
    statut_medical: Optional[Dict] = None
) -> Dict:
    """
    Formate les résultats selon le rôle de l'utilisateur
    
    Args:
        resultats_analyse: Liste des résultats d'analyse de documents
        role: "assureur", "medecin_mh", "agent_technique" ou "agent_production"
        demande_id: ID optionnel de la demande
        statut_medical: Statut de validation du médecin (pour agent_technique et agent_production)
    
    Returns:
        Résultats formatés selon le rôle
    
    WORKFLOW:
        1. medecin_mh → Voit le questionnaire MÉDICAL complet, approuve
        2. agent_technique → Voit le questionnaire ADMINISTRATIF + statut médical
        3. agent_production → Voit TOUT (vue complète)
        4. assureur → Voit les métriques de décision uniquement
    """
    if role == ROLE_MEDECIN_MH:
        return formater_pour_medecin_mh(resultats_analyse, demande_id)
    elif role == ROLE_AGENT_TECHNIQUE:
        return formater_pour_agent_technique(resultats_analyse, demande_id, statut_medical)
    elif role == ROLE_AGENT_PRODUCTION:
        return formater_pour_agent_production(resultats_analyse, demande_id, statut_medical)
    else:
        return formater_pour_assureur(resultats_analyse, demande_id)


def formater_pour_assureur(resultats_analyse: List[Dict], demande_id: Optional[str] = None) -> Dict:
    """
    Formate les résultats pour l'interface Assureur
    
    ⚠️ RESTRICTION: L'assureur NE VOIT PAS le questionnaire médical détaillé
    Il voit uniquement:
        - Métriques de décision (scores, probabilités)
        - Signaux de fraude
        - Informations client de base
        - Avis et recommandations
    """
    if not resultats_analyse:
        return {"error": "Aucun résultat d'analyse", "vue": "assureur"}
    
    # Agrégation des résultats de tous les fichiers
    total_fichiers = len(resultats_analyse)
    fichiers_ok = sum(1 for r in resultats_analyse if r.get("status") == "ok")
    
    # Calcul des moyennes globales
    scores_tous = [
        r["analyse"]["scores"] 
        for r in resultats_analyse 
        if r.get("status") == "ok" and "analyse" in r
    ]
    
    if scores_tous:
        prob_confiance_moyenne = sum(s.get("probabilite_confiance_assureur", 0) for s in scores_tous) / len(scores_tous)
        prob_fraude_moyenne = sum(s.get("probabilite_fraude", 0) for s in scores_tous) / len(scores_tous)
        prob_acceptation_moyenne = sum(s.get("probabilite_acceptation", 0) for s in scores_tous) / len(scores_tous)
        score_coherence_moyen = sum(s.get("score_coherence", 0) for s in scores_tous) / len(scores_tous)
    else:
        prob_confiance_moyenne = prob_fraude_moyenne = prob_acceptation_moyenne = score_coherence_moyen = 0
    
    # Récupérer les infos du client (du premier document valide)
    infos_client = {}
    for resultat in resultats_analyse:
        if resultat.get("status") == "ok" and "analyse" in resultat:
            infos_perso = resultat["analyse"].get("infos_personnelles", {})
            if infos_perso.get("nom") and infos_perso.get("prenom"):
                infos_client = infos_perso
                break
    
    # Collecter tous les signaux de fraude et alertes
    tous_signaux_fraude = []
    toutes_incoherences = []
    documents_expires = []
    documents_flous = []
    
    for resultat in resultats_analyse:
        if resultat.get("status") == "ok" and "analyse" in resultat:
            analyse = resultat["analyse"]
            eval_data = analyse.get("evaluation", {})
            verif = analyse.get("verification_document", {})
            
            tous_signaux_fraude.extend(eval_data.get("signaux_fraude", []))
            toutes_incoherences.extend(eval_data.get("incoherences", []))
            
            if verif.get("est_expire"):
                documents_expires.append(resultat.get("nom_fichier", "Document"))
            
            if verif.get("besoin_nouveau_fichier"):
                documents_flous.append(resultat.get("nom_fichier", "Document"))
    
    # Déterminer l'avis global
    if prob_fraude_moyenne >= 0.5:
        avis_global = "REJET RECOMMANDÉ (FRAUDE SUSPECTÉE)"
        decision_recommandee = "REJETER"
    elif prob_acceptation_moyenne >= 0.7 and prob_fraude_moyenne < 0.3:
        avis_global = "FAVORABLE"
        decision_recommandee = "ACCEPTER"
    elif prob_acceptation_moyenne >= 0.5:
        avis_global = "RÉSERVÉ"
        decision_recommandee = "ACCEPTER SOUS CONDITIONS"
    else:
        avis_global = "DÉFAVORABLE"
        decision_recommandee = "REJETER"
    
    # Niveau de confiance
    if prob_confiance_moyenne >= 0.8:
        niveau_confiance = "TRÈS ÉLEVÉE"
    elif prob_confiance_moyenne >= 0.6:
        niveau_confiance = "ÉLEVÉE"
    elif prob_confiance_moyenne >= 0.4:
        niveau_confiance = "MODÉRÉE"
    else:
        niveau_confiance = "FAIBLE"
    
    # Recommandations
    recommandations = _generer_recommandations_assureur(prob_fraude_moyenne, prob_acceptation_moyenne)
    
    return {
        "vue": "assureur",
        "demande_id": demande_id or f"DEM-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "date_analyse": datetime.now().isoformat(),
        
        "client": {
            "nom": infos_client.get("nom", "N/A"),
            "prenom": infos_client.get("prenom", "N/A"),
            "date_naissance": infos_client.get("date_naissance", "N/A"),
            "sexe": infos_client.get("sexe", "N/A"),
            "telephone": infos_client.get("telephone", "N/A"),
            "email": infos_client.get("email", "N/A"),
            "pays": infos_client.get("pays", "N/A")
        },
        
        "resume": {
            "total_fichiers": total_fichiers,
            "fichiers_analyses": fichiers_ok,
            "fichiers_erreur": total_fichiers - fichiers_ok,
            "avis": avis_global,
            "decision_recommandee": decision_recommandee,
            "niveau_confiance": niveau_confiance
        },
        
        "metriques_principales": {
            "probabilite_acceptation": round(prob_acceptation_moyenne * 100, 1),
            "probabilite_confiance_assureur": round(prob_confiance_moyenne * 100, 1),
            "probabilite_fraude": round(prob_fraude_moyenne * 100, 1),
            "score_coherence": round(score_coherence_moyen, 1)
        },
        
        "verifications": {
            "documents_expires": len(documents_expires) > 0,
            "documents_expires_liste": documents_expires,
            "documents_flous": len(documents_flous) > 0,
            "documents_flous_liste": documents_flous,
            "informations_completes": all(
                r.get("analyse", {}).get("verification_document", {}).get("est_complet", False)
                for r in resultats_analyse if r.get("status") == "ok"
            ),
            "coherence_documents": all(
                r.get("analyse", {}).get("verification_document", {}).get("est_coherent_documents", True)
                for r in resultats_analyse if r.get("status") == "ok"
            )
        },
        
        "alertes": {
            "signaux_fraude": list(set(tous_signaux_fraude))[:10],
            "incoherences": list(set(toutes_incoherences))[:10],
            "total_alertes": len(set(tous_signaux_fraude)) + len(set(toutes_incoherences))
        },
        
        "recommandations": recommandations,
        
        "documents_analyses": [
            {
                "fichier": r.get("nom_fichier", "N/A"),
                "type_document": r.get("analyse", {}).get("type_document", "N/A"),
                "status": r.get("status", "erreur"),
                "avis": r.get("analyse", {}).get("evaluation", {}).get("avis", "N/A") if r.get("status") == "ok" else "ERREUR"
            }
            for r in resultats_analyse
        ],
        
        "message_assureur": _generer_message_assureur(avis_global, prob_confiance_moyenne, prob_fraude_moyenne),
        
        # ⚠️ IMPORTANT: Pas de questionnaire médical pour l'assureur
        "note_restriction": "Le questionnaire médical détaillé n'est accessible que par le Médecin MH"
    }


def formater_pour_medecin_mh(resultats_analyse: List[Dict], demande_id: Optional[str] = None) -> Dict:
    """
    Formate les résultats pour le Médecin MH
    
    ✅ ACCÈS COMPLET: Le Médecin MH a accès au questionnaire médical complet
    Il voit:
        - Questionnaire médical complet (historique, santé actuelle, mode de vie, etc.)
        - Informations personnelles
        - Évaluation médicale détaillée
        - Facteurs de risque médicaux
    """
    if not resultats_analyse:
        return {"error": "Aucun résultat d'analyse", "vue": "medecin_mh"}
    
    # Trouver le questionnaire médical (priorité)
    questionnaire_data = None
    infos_personnelles = {}
    
    for resultat in resultats_analyse:
        if resultat.get("status") == "ok" and "analyse" in resultat:
            analyse = resultat["analyse"]
            
            # Récupérer les infos personnelles
            infos_perso = analyse.get("infos_personnelles", {})
            if infos_perso.get("nom") and not infos_personnelles.get("nom"):
                infos_personnelles = infos_perso
            
            # Chercher le questionnaire médical
            infos_sante = analyse.get("infos_sante", {})
            if infos_sante and any(infos_sante.values()):
                questionnaire_data = infos_sante
                break
    
    # Si pas de questionnaire trouvé, prendre le premier
    if not questionnaire_data:
        for resultat in resultats_analyse:
            if resultat.get("status") == "ok" and "analyse" in resultat:
                questionnaire_data = resultat["analyse"].get("infos_sante", {})
                break
    
    if not questionnaire_data:
        questionnaire_data = {}
    
    # Calculer l'âge si date de naissance disponible
    age = _calculer_age(infos_personnelles.get("date_naissance", ""))
    
    # Calculer le score de risque médical moyen
    scores_risque = [
        r["analyse"]["scores"].get("score_risque", 0)
        for r in resultats_analyse
        if r.get("status") == "ok" and "analyse" in r
    ]
    score_risque_moyen = sum(scores_risque) / len(scores_risque) if scores_risque else 0
    
    # Collecter tous les facteurs de risque
    tous_facteurs_risque = []
    for resultat in resultats_analyse:
        if resultat.get("status") == "ok" and "analyse" in resultat:
            facteurs = resultat["analyse"].get("evaluation", {}).get("facteurs_risque", [])
            tous_facteurs_risque.extend(facteurs)
    
    # Niveau de risque
    if score_risque_moyen >= 0.7:
        niveau_risque = "Très élevé"
    elif score_risque_moyen >= 0.5:
        niveau_risque = "Élevé"
    elif score_risque_moyen >= 0.3:
        niveau_risque = "Modéré"
    else:
        niveau_risque = "Faible"
    
    # Recommandation médicale
    recommandation_medicale = _generer_recommandation_medicale(score_risque_moyen, tous_facteurs_risque)
    
    return {
        "vue": "medecin_mh",
        "demande_id": demande_id or f"DEM-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "date_analyse": datetime.now().isoformat(),
        
        "informations_personnelles": {
            "nom": infos_personnelles.get("nom", "N/A"),
            "prenom": infos_personnelles.get("prenom", "N/A"),
            "date_naissance": infos_personnelles.get("date_naissance", "N/A"),
            "age": age,
            "sexe": infos_personnelles.get("sexe", "N/A"),
            "telephone": infos_personnelles.get("telephone", "N/A"),
            "email": infos_personnelles.get("email", "N/A"),
            "adresse": infos_personnelles.get("adresse", "N/A"),
            "ville": infos_personnelles.get("ville", "N/A"),
            "pays": infos_personnelles.get("pays", "N/A")
        },
        
        # ✅ QUESTIONNAIRE MÉDICAL COMPLET - ACCESSIBLE UNIQUEMENT AU MÉDECIN MH
        "questionnaire_medical_complet": {
            "historique_medical": questionnaire_data.get("historique_medical", {}),
            "sante_actuelle": questionnaire_data.get("sante_actuelle", {}),
            "mode_vie": questionnaire_data.get("mode_vie", {}),
            "allergies": questionnaire_data.get("allergies", {}),
            "sante_mentale": questionnaire_data.get("sante_mentale", {})
        },
        
        "evaluation_medicale": {
            "score_risque_medical": round(score_risque_moyen * 100, 1),
            "niveau_risque": niveau_risque,
            "facteurs_risque": list(set(tous_facteurs_risque)),
            "recommandation_medicale": recommandation_medicale
        },
        
        "documents_medicaux": [
            {
                "fichier": r.get("nom_fichier", "N/A"),
                "type_document": r.get("analyse", {}).get("type_document", "N/A"),
                "date_upload": datetime.now().isoformat(),
                "status": r.get("status", "erreur")
            }
            for r in resultats_analyse
            if r.get("status") == "ok"
        ],
        
        "informations_voyage": {
            "frequence_voyage_mois": infos_personnelles.get("frequence_voyage_mois", ""),
            "frequence_voyage_an": infos_personnelles.get("frequence_voyage_an", ""),
            "destination_habituelle": infos_personnelles.get("destination_habituelle", ""),
            "duree_sejours": infos_personnelles.get("duree_sejours", ""),
            "raison_sejours": infos_personnelles.get("raison_sejours", "")
        },
        
        "message_medecin": _generer_message_medecin(score_risque_moyen, tous_facteurs_risque),
        
        "note_acces": "✅ Accès complet au questionnaire médical (Médecin MH)"
    }


def formater_pour_agent_technique(
    resultats_analyse: List[Dict], 
    demande_id: Optional[str] = None,
    statut_medical: Optional[Dict] = None
) -> Dict:
    """
    Formate les résultats pour l'Agent Technique MH
    
    L'agent technique se concentre sur la VÉRIFICATION DES DOCUMENTS TÉLÉVERSÉS:
        ✅ Analyse des documents (CNI, Passeport, etc.)
        ✅ Détection de fraude sur les documents
        ✅ Incohérences entre documents
        ✅ Validité des documents (expirés, flous, etc.)
        ❌ PAS le questionnaire médical
        ❌ PAS les informations personnelles détaillées
    """
    if not resultats_analyse:
        return {"error": "Aucun résultat d'analyse", "vue": "agent_technique"}
    
    # ═══════════════════════════════════════════════════════════════
    # ANALYSE DES DOCUMENTS TÉLÉVERSÉS
    # ═══════════════════════════════════════════════════════════════
    
    documents_analyses = []
    tous_signaux_fraude = []
    toutes_incoherences = []
    documents_expires = []
    documents_flous = []
    documents_valides = 0
    documents_invalides = 0
    
    for resultat in resultats_analyse:
        if resultat.get("status") == "ok" and "analyse" in resultat:
            analyse = resultat["analyse"]
            verification = analyse.get("verification_document", {})
            evaluation = analyse.get("evaluation", {})
            
            # Collecter les signaux de fraude
            signaux = evaluation.get("signaux_fraude", [])
            tous_signaux_fraude.extend(signaux)
            
            # Collecter les incohérences
            incoherences = evaluation.get("incoherences", [])
            toutes_incoherences.extend(incoherences)
            
            # Vérifier si document expiré
            if verification.get("est_expire"):
                documents_expires.append(resultat.get("nom_fichier"))
                documents_invalides += 1
            elif verification.get("besoin_nouveau_fichier"):
                documents_flous.append(resultat.get("nom_fichier"))
                documents_invalides += 1
            else:
                documents_valides += 1
            
            # Détails du document
            doc_info = {
                "nom_fichier": resultat.get("nom_fichier", "N/A"),
                "type_document": analyse.get("type_document", "Document inconnu"),
                "confiance_ocr": f"{analyse.get('confiance_ocr', 0)}%",
                "verification": {
                    "est_valide": not verification.get("est_expire") and not verification.get("besoin_nouveau_fichier"),
                    "est_expire": verification.get("est_expire", False),
                    "message_expiration": verification.get("message_expiration", ""),
                    "qualite_ok": verification.get("qualite_ok", True),
                    "message_qualite": verification.get("message_qualite", ""),
                    "est_complet": verification.get("est_complet", True),
                    "est_coherent": verification.get("est_coherent_documents", True)
                },
                "dates_document": verification.get("dates_document", {}),
                "signaux_fraude_document": [s for s in signaux if resultat.get("nom_fichier", "") in s] or signaux[:3],
                "status": "✅ VALIDE" if not verification.get("est_expire") and not verification.get("besoin_nouveau_fichier") else "❌ INVALIDE"
            }
            documents_analyses.append(doc_info)
        else:
            documents_analyses.append({
                "nom_fichier": resultat.get("nom_fichier", "N/A"),
                "type_document": "Erreur d'analyse",
                "erreur": resultat.get("erreur", "Erreur inconnue"),
                "status": "❌ ERREUR"
            })
            documents_invalides += 1
    
    # Calculer le score de fraude global
    nb_signaux_fraude = len(set(tous_signaux_fraude))
    nb_incoherences = len(set(toutes_incoherences))
    
    if nb_signaux_fraude >= 3 or documents_expires:
        niveau_fraude = "🚨 CRITIQUE"
        decision_documents = "REJET - Documents frauduleux ou expirés"
    elif nb_signaux_fraude >= 1 or nb_incoherences >= 2:
        niveau_fraude = "⚠️ ÉLEVÉ"
        decision_documents = "VÉRIFICATION MANUELLE REQUISE"
    elif nb_incoherences >= 1:
        niveau_fraude = "⚠️ MODÉRÉ"
        decision_documents = "À SURVEILLER"
    else:
        niveau_fraude = "✅ FAIBLE"
        decision_documents = "DOCUMENTS CONFORMES"
    
    return {
        "vue": "agent_technique",
        "demande_id": demande_id or f"DEM-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "date_analyse": datetime.now().isoformat(),
        
        # ═══════════════════════════════════════════════════════════
        # RÉSUMÉ VÉRIFICATION DOCUMENTS
        # ═══════════════════════════════════════════════════════════
        "resume_verification": {
            "total_documents": len(documents_analyses),
            "documents_valides": documents_valides,
            "documents_invalides": documents_invalides,
            "documents_expires": len(documents_expires),
            "documents_flous": len(documents_flous),
            "niveau_fraude": niveau_fraude,
            "decision": decision_documents
        },
        
        # ═══════════════════════════════════════════════════════════
        # DÉTAIL DES DOCUMENTS ANALYSÉS
        # ═══════════════════════════════════════════════════════════
        "documents_analyses": documents_analyses,
        
        # ═══════════════════════════════════════════════════════════
        # ALERTES FRAUDE ET INCOHÉRENCES
        # ═══════════════════════════════════════════════════════════
        "alertes": {
            "signaux_fraude": list(set(tous_signaux_fraude))[:10],
            "nb_signaux_fraude": nb_signaux_fraude,
            "incoherences": list(set(toutes_incoherences))[:10],
            "nb_incoherences": nb_incoherences,
            "documents_expires": documents_expires,
            "documents_mauvaise_qualite": documents_flous
        },
        
        # ═══════════════════════════════════════════════════════════
        # RECOMMANDATIONS AGENT TECHNIQUE
        # ═══════════════════════════════════════════════════════════
        "recommandations": _generer_recommandations_documents(
            documents_expires, 
            documents_flous, 
            tous_signaux_fraude, 
            toutes_incoherences
        ),
        
        "note_acces": "🔍 Vue Agent Technique - Vérification des documents téléversés uniquement"
    }


def _generer_recommandations_documents(
    documents_expires: List[str],
    documents_flous: List[str],
    signaux_fraude: List[str],
    incoherences: List[str]
) -> List[str]:
    """Génère les recommandations pour l'agent technique"""
    recommandations = []
    
    if documents_expires:
        recommandations.append(f"⛔ REJET: {len(documents_expires)} document(s) expiré(s) - Demander nouveaux documents")
    
    if documents_flous:
        recommandations.append(f"📄 Demander de retéléverser {len(documents_flous)} document(s) de meilleure qualité")
    
    if len(signaux_fraude) >= 3:
        recommandations.append("🚨 FRAUDE SUSPECTÉE: Vérification manuelle des documents originaux obligatoire")
    elif len(signaux_fraude) >= 1:
        recommandations.append("⚠️ Vérifier l'authenticité des documents auprès des autorités")
    
    if len(incoherences) >= 2:
        recommandations.append("⚠️ Incohérences multiples détectées - Contacter le client pour clarification")
    elif len(incoherences) >= 1:
        recommandations.append("ℹ️ Vérifier les informations incohérentes avec le client")
    
    if not recommandations:
        recommandations.append("✅ Documents conformes - Aucune action requise")
    
    return recommandations


def formater_pour_agent_production(
    resultats_analyse: List[Dict], 
    demande_id: Optional[str] = None,
    statut_medical: Optional[Dict] = None
) -> Dict:
    """
    Formate les résultats pour l'Agent de Production
    
    L'agent de production a accès à TOUT pour donner l'approbation finale:
        ✅ Questionnaire médical complet
        ✅ Informations personnelles (questionnaire administratif)
        ✅ Vérification des documents (fraude, incohérences)
        ✅ Scores IA complets
        ✅ Statuts de toutes les validations
        ✅ Clauses d'exclusion
    """
    if not resultats_analyse:
        return {"error": "Aucun résultat d'analyse", "vue": "agent_production"}
    
    # Obtenir la vue médecin (questionnaire médical complet)
    vue_medecin = formater_pour_medecin_mh(resultats_analyse, demande_id)
    
    # Obtenir la vue agent technique (vérification documents)
    vue_technique = formater_pour_agent_technique(resultats_analyse, demande_id, statut_medical)
    
    # Obtenir la vue assureur (scores)
    vue_assureur = formater_pour_assureur(resultats_analyse, demande_id)
    
    # Récupérer les infos personnelles
    infos_personnelles = vue_medecin.get("informations_personnelles", {})
    
    # Collecter les facteurs de risque
    facteurs_risque = []
    for resultat in resultats_analyse:
        if resultat.get("status") == "ok" and "analyse" in resultat:
            facteurs = resultat["analyse"].get("evaluation", {}).get("facteurs_risque", [])
            facteurs_risque.extend(facteurs)
    
    # Statut médical par défaut
    if statut_medical is None:
        statut_medical = {
            "statut": "EN_ATTENTE",
            "approuve_par": None,
            "date_approbation": None,
            "commentaire": "En attente de validation par le médecin"
        }
    
    # Statut technique par défaut
    statut_technique = {
        "statut": "EN_ATTENTE",
        "approuve_par": None,
        "date_approbation": None,
        "commentaire": "En attente de validation technique"
    }
    
    # Déterminer si prêt pour approbation
    verification_docs = vue_technique.get("resume_verification", {})
    docs_ok = verification_docs.get("niveau_fraude") == "✅ FAIBLE"
    medical_ok = statut_medical.get("statut") == "APPROUVE"
    
    # Calcul des totaux d'analyse
    total_documents = len(resultats_analyse)
    documents_ok = sum(1 for r in resultats_analyse if r.get("status") == "ok")
    documents_erreur = total_documents - documents_ok
    
    # Collecter toutes les incohérences et signaux de fraude DÉTAILLÉS
    toutes_incoherences = []
    tous_signaux_fraude = []
    details_par_document = []
    
    for resultat in resultats_analyse:
        nom_fichier = resultat.get("nom_fichier", "Document")
        if resultat.get("status") == "ok" and "analyse" in resultat:
            analyse = resultat["analyse"]
            evaluation = analyse.get("evaluation", {})
            verification = analyse.get("verification_document", {})
            scores = analyse.get("scores", {})
            
            # Collecter incohérences et signaux
            incoherences_doc = evaluation.get("incoherences", [])
            signaux_doc = evaluation.get("signaux_fraude", [])
            toutes_incoherences.extend(incoherences_doc)
            tous_signaux_fraude.extend(signaux_doc)
            
            # Détails par document pour l'agent de production
            details_par_document.append({
                "document": nom_fichier,
                "type": analyse.get("type_document", "Inconnu"),
                "confiance_ocr": f"{analyse.get('confiance_ocr', 0):.1f}%",
                "statut": "✅ VALIDE" if not verification.get("est_expire") and not verification.get("besoin_nouveau_fichier") else "❌ INVALIDE",
                "problemes_detectes": incoherences_doc + signaux_doc,
                "score_acceptation": f"{scores.get('probabilite_acceptation', 0) * 100:.1f}%",
                "score_fraude": f"{scores.get('probabilite_fraude', 0) * 100:.1f}%"
            })
        else:
            details_par_document.append({
                "document": nom_fichier,
                "type": "Erreur",
                "statut": "❌ ERREUR",
                "erreur": resultat.get("erreur", "Erreur inconnue")
            })
    
    # Scores moyens
    scores_acceptation = []
    scores_fraude = []
    scores_coherence = []
    scores_confiance = []
    for resultat in resultats_analyse:
        if resultat.get("status") == "ok" and "analyse" in resultat:
            scores = resultat["analyse"].get("scores", {})
            if scores.get("probabilite_acceptation"):
                scores_acceptation.append(scores["probabilite_acceptation"])
            if scores.get("probabilite_fraude"):
                scores_fraude.append(scores["probabilite_fraude"])
            if scores.get("score_coherence"):
                scores_coherence.append(scores["score_coherence"])
            if scores.get("probabilite_confiance_assureur"):
                scores_confiance.append(scores["probabilite_confiance_assureur"])
    
    prob_acceptation_moyenne = sum(scores_acceptation) / len(scores_acceptation) if scores_acceptation else 0
    prob_fraude_moyenne = sum(scores_fraude) / len(scores_fraude) if scores_fraude else 0
    score_coherence_moyen = sum(scores_coherence) / len(scores_coherence) if scores_coherence else 0
    score_confiance_moyen = sum(scores_confiance) / len(scores_confiance) if scores_confiance else 0
    
    # Décision finale automatique avec LOGIQUE AMÉLIORÉE
    verification_ok = verification_docs.get("niveau_fraude") == "✅ FAIBLE"
    risque_medical = vue_medecin.get("evaluation_medicale", {}).get("niveau_risque", "Faible")
    nb_incoherences = len(set(toutes_incoherences))
    nb_signaux_fraude = len(set(tous_signaux_fraude))
    
    # Calcul du score global d'acceptation (0-100)
    score_global = 0
    if prob_acceptation_moyenne > 0:
        score_global += prob_acceptation_moyenne * 40  # 40% du score
    if score_coherence_moyen > 0:
        score_global += (score_coherence_moyen / 100) * 30  # 30% du score
    if score_confiance_moyen > 0:
        score_global += score_confiance_moyen * 20  # 20% du score
    # Pénalité pour fraude
    score_global -= prob_fraude_moyenne * 10  # -10% si fraude
    score_global = max(0, min(100, score_global))
    
    # Déterminer la décision finale
    if prob_fraude_moyenne >= 0.5 or nb_signaux_fraude >= 5:
        decision_finale = "❌ REJET RECOMMANDÉ"
        motif_decision = f"Fraude suspectée: {nb_signaux_fraude} signal(s) de fraude détecté(s), probabilité de fraude {prob_fraude_moyenne*100:.1f}%"
        couleur_decision = "rouge"
    elif nb_incoherences >= 5:
        decision_finale = "❌ REJET RECOMMANDÉ"
        motif_decision = f"Trop d'incohérences détectées ({nb_incoherences})"
        couleur_decision = "rouge"
    elif not verification_ok or verification_docs.get("documents_invalides", 0) > 0:
        decision_finale = "⚠️ EN ATTENTE - Documents à vérifier"
        motif_decision = f"Documents invalides ou de mauvaise qualité ({verification_docs.get('documents_invalides', 0)} document(s) invalide(s))"
        couleur_decision = "orange"
    elif risque_medical in ["Élevé", "Très élevé"]:
        decision_finale = "⚠️ ACCEPTATION SOUS CONDITIONS"
        motif_decision = f"Risque médical {risque_medical} - Clauses d'exclusion requises"
        couleur_decision = "orange"
    elif prob_acceptation_moyenne >= 0.7 and prob_fraude_moyenne < 0.2:
        decision_finale = "✅ ACCEPTATION RECOMMANDÉE"
        motif_decision = "Dossier conforme, aucun risque majeur détecté"
        couleur_decision = "vert"
    elif prob_acceptation_moyenne >= 0.5:
        decision_finale = "✅ ACCEPTATION POSSIBLE"
        motif_decision = "Dossier acceptable avec quelques réserves mineures"
        couleur_decision = "vert"
    else:
        decision_finale = "⚠️ ÉTUDE APPROFONDIE REQUISE"
        motif_decision = "Probabilité d'acceptation faible, vérification manuelle conseillée"
        couleur_decision = "orange"
    
    # Actions requises pour l'agent de production
    actions_requises = []
    if not verification_ok:
        actions_requises.append("📄 Vérifier les documents de mauvaise qualité")
    if nb_incoherences > 0:
        actions_requises.append(f"🔍 Examiner les {nb_incoherences} incohérence(s) détectée(s)")
    if nb_signaux_fraude > 0:
        actions_requises.append(f"🚨 Vérifier les {nb_signaux_fraude} signal(aux) de fraude")
    if risque_medical in ["Élevé", "Très élevé"]:
        actions_requises.append("⚕️ Vérifier l'approbation médicale")
    if not medical_ok:
        actions_requises.append("👨‍⚕️ Attendre la validation du médecin MH")
    if not actions_requises:
        actions_requises.append("✅ Aucune action particulière requise - Dossier prêt pour approbation")
    
    return {
        "vue": "agent_production",
        "demande_id": demande_id or f"DEM-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "date_analyse": datetime.now().isoformat(),
        
        # ╔══════════════════════════════════════════════════════════════════════════╗
        # ║                    🎯 RÉSUMÉ EXÉCUTIF - DÉCISION                         ║
        # ╚══════════════════════════════════════════════════════════════════════════╝
        "resume_executif": {
            "decision_ia": decision_finale,
            "motif_decision": motif_decision,
            "couleur_decision": couleur_decision,
            "score_global_acceptation": f"{score_global:.1f}/100",
            "confiance_ia": f"{score_confiance_moyen * 100:.1f}%",
            "actions_requises": actions_requises,
            "pret_pour_approbation": medical_ok and docs_ok and nb_signaux_fraude < 3
        },
        
        # ═══════════════════════════════════════════════════════════════════════════
        # 📊 STATISTIQUES D'ANALYSE
        # ═══════════════════════════════════════════════════════════════════════════
        "statistiques_analyse": {
            "total_documents_analyses": total_documents,
            "documents_traites_ok": documents_ok,
            "documents_en_erreur": documents_erreur,
            "total_incoherences": nb_incoherences,
            "total_signaux_fraude": nb_signaux_fraude,
            "score_coherence_global": f"{score_coherence_moyen:.1f}/100"
        },
        
        # ═══════════════════════════════════════════════════════════════════════════
        # 📈 SCORES IA DÉTAILLÉS
        # ═══════════════════════════════════════════════════════════════════════════
        "scores_ia_detailles": {
            "probabilite_acceptation": f"{prob_acceptation_moyenne * 100:.1f}%",
            "probabilite_acceptation_brut": prob_acceptation_moyenne,
            "probabilite_fraude": f"{prob_fraude_moyenne * 100:.1f}%",
            "probabilite_fraude_brut": prob_fraude_moyenne,
            "score_coherence": f"{score_coherence_moyen:.1f}/100",
            "score_confiance_assureur": f"{score_confiance_moyen * 100:.1f}%",
            "score_global": f"{score_global:.1f}/100",
            "interpretation": {
                "acceptation": "Élevée" if prob_acceptation_moyenne >= 0.7 else "Moyenne" if prob_acceptation_moyenne >= 0.5 else "Faible",
                "fraude": "Critique" if prob_fraude_moyenne >= 0.5 else "Élevée" if prob_fraude_moyenne >= 0.3 else "Faible",
                "coherence": "Excellente" if score_coherence_moyen >= 90 else "Bonne" if score_coherence_moyen >= 70 else "À vérifier"
            }
        },
        
        # ═══════════════════════════════════════════════════════════════════════════
        # 🚨 PROBLÈMES DÉTECTÉS (INCOHÉRENCES & FRAUDE)
        # ═══════════════════════════════════════════════════════════════════════════
        "problemes_detectes": {
            "resume": f"{nb_incoherences} incohérence(s) et {nb_signaux_fraude} signal(aux) de fraude détecté(s)",
            "incoherences": {
                "nombre": nb_incoherences,
                "liste_detaillee": list(set(toutes_incoherences)),
                "gravite": "Critique" if nb_incoherences >= 5 else "Élevée" if nb_incoherences >= 3 else "Modérée" if nb_incoherences >= 1 else "Aucune"
            },
            "signaux_fraude": {
                "nombre": nb_signaux_fraude,
                "liste_detaillee": list(set(tous_signaux_fraude)),
                "gravite": "Critique" if nb_signaux_fraude >= 5 else "Élevée" if nb_signaux_fraude >= 3 else "Modérée" if nb_signaux_fraude >= 1 else "Aucune"
            }
        },
        
        # ═══════════════════════════════════════════════════════════════════════════
        # 📄 DÉTAIL PAR DOCUMENT ANALYSÉ
        # ═══════════════════════════════════════════════════════════════════════════
        "analyse_par_document": details_par_document,
        
        # ═══════════════════════════════════════════════════════════════════════════
        # 👤 INFORMATIONS CLIENT
        # ═══════════════════════════════════════════════════════════════════════════
        "client": {
            "informations_personnelles": infos_personnelles,
            "resume": {
                "nom_complet": f"{infos_personnelles.get('prenom', '')} {infos_personnelles.get('nom', '')}".strip() or "Non renseigné",
                "age": infos_personnelles.get("age", "Non calculé"),
                "contact": infos_personnelles.get("email", "") or infos_personnelles.get("telephone", "") or "Non renseigné"
            }
        },
        
        # ═══════════════════════════════════════════════════════════════════════════
        # ⚕️ ÉVALUATION MÉDICALE
        # ═══════════════════════════════════════════════════════════════════════════
        "evaluation_medicale": {
            "questionnaire_medical": vue_medecin.get("questionnaire_medical_complet", {}),
            "resume_medical": vue_medecin.get("evaluation_medicale", {}),
            "risque_medical": risque_medical,
            "facteurs_risque": list(set(facteurs_risque)),
            "recommandation_medicale": vue_medecin.get("evaluation_medicale", {}).get("recommandation_medicale", "Non évaluée")
        },
        
        # ═══════════════════════════════════════════════════════════════════════════
        # 📋 STATUTS DES VALIDATIONS
        # ═══════════════════════════════════════════════════════════════════════════
        "statuts_validations": {
            "validation_medicale": {
                "statut": statut_medical.get("statut", "EN_ATTENTE"),
                "icone": "✅" if statut_medical.get("statut") == "APPROUVE" else "⏳",
                "approuve_par": statut_medical.get("approuve_par"),
                "date_approbation": statut_medical.get("date_approbation"),
                "commentaire": statut_medical.get("commentaire", "")
            },
            "validation_technique": {
                "statut": "APPROUVE" if docs_ok else "EN_ATTENTE",
                "icone": "✅" if docs_ok else "⏳",
                "niveau_fraude": verification_docs.get("niveau_fraude", "N/A"),
                "decision_documents": verification_docs.get("decision", "N/A")
            },
            "resume_validations": {
                "medical": "✅ Approuvé" if medical_ok else "⏳ En attente",
                "technique": "✅ Approuvé" if docs_ok else "⏳ En attente",
                "pret_approbation_finale": medical_ok and docs_ok
            }
        },
        
        # ═══════════════════════════════════════════════════════════════════════════
        # 📄 VÉRIFICATION DOCUMENTS DÉTAILLÉE
        # ═══════════════════════════════════════════════════════════════════════════
        "verification_documents": {
            "resume": vue_technique.get("resume_verification", {}),
            "documents_analyses": vue_technique.get("documents_analyses", []),
            "alertes_documents": vue_technique.get("alertes", {}),
            "recommandations_documents": vue_technique.get("recommandations", [])
        },
        
        
        # ═══════════════════════════════════════════════════════════════════════════
        # 💡 RECOMMANDATIONS FINALES
        # ═══════════════════════════════════════════════════════════════════════════
        "recommandations_finales": {
            "actions_immediates": actions_requises,
            "recommandations_assureur": vue_assureur.get("recommandations", []),
            "message_final": _generer_message_agent_production(
                decision_finale, score_global, prob_fraude_moyenne, 
                nb_incoherences, risque_medical, medical_ok, docs_ok
            )
        },
        
        # Données legacy pour compatibilité
        "resume_analyse": {
            "total_documents_analyses": total_documents,
            "documents_traites_ok": documents_ok,
            "documents_en_erreur": documents_erreur,
            "total_incoherences": nb_incoherences,
            "total_signaux_fraude": nb_signaux_fraude,
            "score_coherence_global": f"{score_coherence_moyen:.1f}/100"
        },
        "decision_finale": {
            "decision": decision_finale,
            "motif": motif_decision,
            "probabilite_acceptation": f"{prob_acceptation_moyenne * 100:.1f}%",
            "probabilite_fraude": f"{prob_fraude_moyenne * 100:.1f}%",
            "risque_medical": risque_medical,
            "documents_conformes": verification_ok
        },
        "incoherences_detectees": {
            "nombre": nb_incoherences,
            "liste": list(set(toutes_incoherences))[:10],
            "signaux_fraude": list(set(tous_signaux_fraude))[:10]
        },
        "resume_global": {
            "client": vue_assureur.get("client", {}),
            "avis_ia": vue_assureur.get("resume", {}).get("avis", "N/A"),
            "decision_recommandee": vue_assureur.get("resume", {}).get("decision_recommandee", "N/A"),
            "niveau_confiance": vue_assureur.get("resume", {}).get("niveau_confiance", "N/A")
        },
        "validations": {
            "validation_medicale": {
                "statut": statut_medical.get("statut", "EN_ATTENTE"),
                "approuve_par": statut_medical.get("approuve_par"),
                "date_approbation": statut_medical.get("date_approbation"),
                "commentaire": statut_medical.get("commentaire", "")
            },
            "validation_technique": {
                "statut": "APPROUVE" if docs_ok else "EN_ATTENTE",
                "niveau_fraude": verification_docs.get("niveau_fraude", "N/A"),
                "decision_documents": verification_docs.get("decision", "N/A")
            },
            "pret_pour_approbation": medical_ok and docs_ok
        },
        "scores_ia": vue_assureur.get("metriques_principales", {}),
        "alertes": vue_assureur.get("alertes", {}),
        "questionnaire_medical": vue_medecin.get("questionnaire_medical_complet", {}),
        "informations_personnelles": infos_personnelles,
        
        "note_acces": "✅ Vue Agent de Production - Approbation finale"
    }


def _generer_message_agent_production(decision: str, score_global: float, prob_fraude: float,
                                       nb_incoherences: int, risque_medical: str,
                                       medical_ok: bool, docs_ok: bool) -> str:
    """Génère un message résumé clair pour l'agent de production"""
    messages = []
    
    messages.append("═" * 60)
    messages.append("📋 RAPPORT D'ANALYSE IA - MOBILITY HEALTH")
    messages.append("═" * 60)
    
    # Décision principale
    messages.append(f"\n🎯 DÉCISION IA: {decision}")
    messages.append(f"📊 Score global d'acceptation: {score_global:.1f}/100")
    
    # Analyse des risques
    messages.append(f"\n📈 ANALYSE DES RISQUES:")
    messages.append(f"  • Probabilité de fraude: {prob_fraude*100:.1f}%")
    messages.append(f"  • Incohérences détectées: {nb_incoherences}")
    messages.append(f"  • Risque médical: {risque_medical}")
    
    # Statut des validations
    messages.append(f"\n✓ STATUT DES VALIDATIONS:")
    messages.append(f"  • Validation médicale: {'✅ Approuvée' if medical_ok else '⏳ En attente'}")
    messages.append(f"  • Validation technique: {'✅ Approuvée' if docs_ok else '⏳ En attente'}")
    
    # Conclusion
    messages.append(f"\n{'═' * 60}")
    if "ACCEPTATION RECOMMANDÉE" in decision or "ACCEPTATION POSSIBLE" in decision:
        messages.append("✅ CONCLUSION: Dossier favorable - Approbation recommandée")
    elif "REJET" in decision:
        messages.append("❌ CONCLUSION: Dossier défavorable - Rejet recommandé")
    else:
        messages.append("⚠️ CONCLUSION: Vérifications supplémentaires nécessaires")
    messages.append("═" * 60)
    
    messages.append("\n⚠️ NOTE: Cette analyse IA est une aide à la décision.")
    messages.append("   La décision finale reste celle de l'Agent de Production.")
    
    return "\n".join(messages)


# ═══════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES PRIVÉES
# ═══════════════════════════════════════════════════════════════

def _calculer_age(date_naissance: str) -> Optional[int]:
    """Calcule l'âge à partir de la date de naissance"""
    if not date_naissance:
        return None
    
    try:
        from datetime import date
        for sep in ["/", "-"]:
            parts = date_naissance.split(sep)
            if len(parts) == 3:
                jour, mois, annee = int(parts[0]), int(parts[1]), int(parts[2])
                if annee < 100:
                    annee = 2000 + annee if annee < 50 else 1900 + annee
                return date.today().year - annee
    except:
        pass
    return None


def _generer_recommandations_assureur(prob_fraude: float, prob_acceptation: float) -> List[str]:
    """Génère les recommandations pour l'assureur"""
    recommandations = []
    
    if prob_fraude >= 0.5:
        recommandations.append("⛔ Vérification approfondie requise")
        recommandations.append("Contrôle des documents originaux nécessaire")
        recommandations.append("Investigation supplémentaire recommandée")
    elif prob_acceptation < 0.3:
        recommandations.append("Examen médical approfondi requis")
        recommandations.append("Évaluation par un médecin conseil obligatoire")
    elif prob_acceptation < 0.5:
        recommandations.append("Examen médical complémentaire recommandé")
        recommandations.append("Surprime possible selon l'évaluation")
    else:
        recommandations.append("Demande conforme aux critères standards")
        recommandations.append("Traitement standard recommandé")
    
    return recommandations


def _generer_recommandation_medicale(score_risque: float, facteurs_risque: List[str]) -> str:
    """Génère la recommandation médicale"""
    if score_risque >= 0.5:
        return "Examen médical approfondi requis. Facteurs de risque multiples détectés."
    elif score_risque >= 0.3:
        return "Examen médical complémentaire recommandé."
    elif facteurs_risque:
        return "Surveillance médicale recommandée."
    else:
        return "Aucun facteur de risque majeur détecté. Acceptation médicale recommandée."


def _generer_message_assureur(avis: str, confiance: float, fraude: float) -> str:
    """Génère un message synthétique pour l'assureur"""
    if fraude >= 0.5:
        return f"⚠️ FRAUDE SUSPECTÉE ({fraude:.0%}) - Vérification approfondie requise"
    elif confiance >= 0.8:
        return f"✅ Demande très fiable ({confiance:.0%} de confiance) - Acceptation standard recommandée"
    elif confiance >= 0.6:
        return f"✅ Demande fiable ({confiance:.0%} de confiance) - Traitement standard recommandé"
    elif confiance >= 0.4:
        return f"⚠️ Demande acceptable ({confiance:.0%} de confiance) - Vérification complémentaire recommandée"
    else:
        return f"⚠️ Demande à risque ({confiance:.0%} de confiance) - Examen approfondi requis"


def _generer_message_medecin(score_risque: float, facteurs_risque: List[str]) -> str:
    """Génère un message synthétique pour le médecin"""
    if score_risque >= 0.5:
        return f"⚠️ Risque médical élevé ({score_risque:.0%}) - {len(facteurs_risque)} facteur(s) de risque détecté(s)"
    elif score_risque >= 0.3:
        return f"⚠️ Risque médical modéré ({score_risque:.0%}) - Surveillance recommandée"
    elif facteurs_risque:
        return f"✅ Risque médical faible ({score_risque:.0%}) - Quelques facteurs mineurs"
    else:
        return f"✅ Aucun facteur de risque majeur - Patient en bonne santé"

