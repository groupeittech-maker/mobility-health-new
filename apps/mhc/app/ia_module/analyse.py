# analyse.py - Module d'analyse IA pour formulaires de souscription
import os
import re
import pickle
from datetime import datetime, date
from pdf2image import convert_from_path
from PIL import Image, ImageFilter, ImageEnhance
import pytesseract
import filetype
from sklearn.linear_model import LogisticRegression
import numpy as np

# --- Import de la configuration ---
try:
    from app.ia_module.config import config
    pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD
    POPPLER_PATH = config.POPPLER_PATH
except ImportError:
    # Fallback si import échoue (pour tests directs)
    from .config import config
    pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD
    POPPLER_PATH = config.POPPLER_PATH

# --- OCR PDF / Image avec calcul de confiance amélioré ---
def extraire_texte_ocr(filepath):
    """
    Extrait le texte depuis PDF ou image avec calcul de confiance OCR réel
    """
    texte_total = ""
    confiances = []
    kind = filetype.guess(filepath)
    mime = kind.mime if kind else ("application/pdf" if filepath.lower().endswith(".pdf") else "image/png")
    
    try:
        if "pdf" in mime.lower():
            pages = convert_from_path(filepath, poppler_path=POPPLER_PATH, dpi=300)
            for idx, img in enumerate(pages):
                # Amélioration de l'image pour meilleure OCR
                img = img.convert("L")  # Grayscale
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(2.0)
                img = img.filter(ImageFilter.MedianFilter(size=3))
                
                # Extraction avec données de confiance
                data = pytesseract.image_to_data(img, lang="fra+eng", output_type=pytesseract.Output.DICT)
                
                # Calcul de la confiance moyenne
                confs = [int(conf) for conf in data['conf'] if conf != '-1']
                if confs:
                    confiances.extend(confs)
                
                # Extraction du texte
                texte_page = pytesseract.image_to_string(img, lang="fra+eng")
                texte_total += texte_page + "\n"
        else:
            # Traitement image
            img = Image.open(filepath)
            img = img.convert("L")
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)
            img = img.filter(ImageFilter.MedianFilter(size=3))
            
            # Extraction avec confiance
            data = pytesseract.image_to_data(img, lang="fra+eng", output_type=pytesseract.Output.DICT)
            confs = [int(conf) for conf in data['conf'] if conf != '-1']
            if confs:
                confiances.extend(confs)
            
            texte_total = pytesseract.image_to_string(img, lang="fra+eng")
    
    except Exception as e:
        print(f"Erreur OCR : {e}")
        confiance = 0.3
        return texte_total.strip(), mime, confiance
    
    # Calcul de la confiance moyenne (0-100 -> 0-1)
    confiance = np.mean(confiances) / 100.0 if confiances else 0.5
    confiance = max(0.0, min(1.0, confiance))  # Normaliser entre 0 et 1
    
    # Nettoyage du texte
    texte_total = re.sub(r"\s+", " ", texte_total)
    return texte_total.strip(), mime, confiance

# --- Extraction complète des informations personnelles ---
def extraire_infos_personnelles(texte):
    """
    Extrait toutes les informations personnelles du formulaire
    """
    champs_perso = {
        "nom": [
            r"Nom\s*:\s*([A-Z][A-Z\-']+)",
            r"Nom\s*[:•]\s*([A-Z][a-zA-Z\-']+)"
        ],
        "prenom": [
            r"Pr[eé]nom\s*:\s*([A-Za-z][a-zA-Z\-']+)",
            r"Pr[eé]nom\s*[:•]\s*([A-Za-z][a-zA-Z\-']+)"
        ],
        "date_naissance": [
            r"Date\s+de\s+naissance\s*:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"Date\s+naissance\s*:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"N[eé]\s+le\s*:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
        ],
        "sexe": [
            r"Sexe\s*:\s*(M|F|Homme|Femme|Masculin|F[eé]minin)",
            r"Sexe\s*[:•]\s*(M|F|Homme|Femme|Masculin|F[eé]minin)"
        ],
        "telephone": [
            r"T[eé]l[eé]phone\s*:\s*([+\d\s\-\(\)]{8,20})",
            r"T[eé]l\s*:\s*([+\d\s\-\(\)]{8,20})"
        ],
        "whatsapp": [
            r"Whatsapp\s*:\s*([+\d\s\-\(\)]{8,20})",
            r"Whatsapp\s*[:•]\s*([+\d\s\-\(\)]{8,20})"
        ],
        "email": [
            r"[Ee]-?[Mm]ail\s*:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
            r"Courriel\s*:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
        ],
        "adresse": [
            r"Adresse\s*:\s*([^:]{5,60}?)(?:\s+Ville|\s+Pays|\s+T[eé]l)",
            r"Adresse\s*[:•]\s*(.{5,60}?)(?=\s+Ville|\s+Pays|\s+T[eé]l)"
        ],
        "ville": [
            r"Ville\s*:\s*([A-Za-z][a-zA-Z\s\-']+?)(?:\s+Pays|\s+T[eé]l|\s+[0-9])",
            r"Ville\s*[:•]\s*([A-Za-z][a-zA-Z\s\-']+)"
        ],
        "pays": [
            r"Pays\s*:\s*([A-Za-z][a-zA-Zéèêëàâäùûüôöîïç\-]+)",
            r"Nationalit[eé]\s*:\s*([A-Za-z][a-zA-Zéèêëàâäùûüôöîïç\-]+)"
        ],
        "marie": [
            r"Marié\(e\)\s*[:•]\s*(Oui|Non|OUI|NON)(?:\s|$|\n|Nbre|Fréquence)",
            r"Marié\(e\)\s+(Oui|Non|OUI|NON)(?:\s|$|\n|Nbre|Fréquence)"
        ],
        "nb_enfants": [
            r"Nbre\s+d['']enfants\s+sous\s+votre\s+responsabilité\s*[:•]\s*(\d+)",
            r"enfants\s+sous\s+votre\s+responsabilité\s*[:•]\s*(\d+)",
            r"Nbre\s+d['']enfants\s*[:•]\s*(\d+)"
        ],
        "frequence_voyage_mois": [
            r"Fréquence\s+de\s+voyage.*?Par\s+mois\s*[:•]\s*(\d+)",
            r"Par\s+mois\s*[:•]\s*(\d+)"
        ],
        "frequence_voyage_an": [
            r"Par\s+an\s*[:•]\s*(\d+)",
            r"Fréquence\s+de\s+voyage.*?Par\s+an\s*[:•]\s*(\d+)"
        ],
        "destination_habituelle": [
            r"Destination\s+habituelle\s*[:•]\s*(Afrique|Europe|Amérique|Asie|Autre)(?:\s|$|\n|Durée)",
            r"Destination\s+habituelle.*?(Afrique|Europe|Amérique|Asie|Autre)(?:\s|$|\n|Durée)"
        ],
        "duree_sejours": [
            r"Durée\s+moyenne\s+de\s+vos\s+séjours\s*[:•]\s*(Moins\s+de\s+1\s+mois|2\s+mois|3\s+mois|Plus\s+de\s+3\s+mois)",
            r"(Moins\s+de\s+1\s+mois|2\s+mois|3\s+mois|Plus\s+de\s+3\s+mois)"
        ],
        "raison_sejours": [
            r"Raison\s+principale\s+de\s+vos\s+séjours\s*[:•]\s*(Professionnelle|Tourisme|Vacance|Familiale|Religieux|Autres)(?:\s|$|\n)",
            r"(Professionnelle|Tourisme|Vacance|Familiale|Religieux|Autres)"
        ]
    }
    
    infos = {}
    for champ, patterns in champs_perso.items():
        infos[champ] = ""
        for pattern in patterns:
            match = re.search(pattern, texte, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                valeur = match.group(1).strip() if match.lastindex else match.group(0).strip()
                # Nettoyer la valeur : enlever les caractères indésirables en fin
                valeur = re.sub(r'[^\w\s@.\-+()/:]+$', '', valeur).strip()
                # Limiter la longueur pour éviter les captures trop longues
                if len(valeur) <= 200:  # Limite raisonnable
                    infos[champ] = valeur
                break
    
    return infos

# --- Extraction complète des informations de santé ---
def extraire_infos_sante(texte):
    """
    Extrait toutes les informations médicales selon les 6 sections du formulaire
    """
    data = {
        "historique_medical": {},
        "sante_actuelle": {},
        "mode_vie": {},
        "allergies": {},
        "sante_mentale": {},
        "voyage": {}
    }
    
    # === SECTION 1: HISTORIQUE MÉDICAL ===
    maladies = [
        "Hypertension art[éèe]rielle",
        "Diab[éèe]te",
        "Maladies cardiaques",
        "Maladies respiratoires",
        "Maladies neurologiques",
        "Maladies chroniques",
        "Aucune"
    ]
    
    maladie_noms = [
        "Hypertension artérielle",
        "Diabète",
        "Maladies cardiaques",
        "Maladies respiratoires",
        "Maladies neurologiques",
        "Maladies chroniques",
        "Aucune de ces maladies"
    ]
    
    for maladie_pattern, maladie_nom in zip(maladies, maladie_noms):
        # Chercher le pattern "Maladie : Oui" ou "Maladie : Non"
        # Note: L'OCR peut lire "Oui" comme "Qui" ou "0ui"
        pattern_oui = rf"{maladie_pattern}\s*:\s*(Oui|OUI|oui|Qui|QUI|qui|0ui)"
        pattern_non = rf"{maladie_pattern}\s*:\s*(Non|NON|non|N0n)"
        
        if re.search(pattern_oui, texte, re.IGNORECASE):
            data["historique_medical"][maladie_nom] = True
        elif re.search(pattern_non, texte, re.IGNORECASE):
            data["historique_medical"][maladie_nom] = False
        else:
            data["historique_medical"][maladie_nom] = False
    
    # Maladies cardiaques - précision
    match_card = re.search(r"Maladies\s+cardiaques.*?Précisez\s*[:•]\s*([^\n\r]+)", texte, re.IGNORECASE | re.DOTALL)
    data["historique_medical"]["maladies_cardiaques_details"] = match_card.group(1).strip() if match_card else ""
    
    # Traitement médical régulier
    match_traitement = re.search(r"traitement\s+médical\s+régulier\??\s*(Oui|Non|OUI|NON)", texte, re.IGNORECASE)
    data["historique_medical"]["traitement_regulier"] = match_traitement.group(1).strip() if match_traitement else "Non"
    
    # Type de traitement
    match_type_traitement = re.search(r"Si\s+oui.*?type\s+de\s+traitement\s*[:•]\s*([^\n\r]+)", texte, re.IGNORECASE | re.DOTALL)
    data["historique_medical"]["type_traitement"] = match_type_traitement.group(1).strip() if match_type_traitement else ""
    
    # Hospitalisation récente
    match_hosp = re.search(r"hospitalisé\s+au\s+cours\s+des\s+12\s+derniers\s+mois\??\s*(Oui|Non|OUI|NON)", texte, re.IGNORECASE)
    data["historique_medical"]["hospitalisation_recente"] = match_hosp.group(1).strip() if match_hosp else "Non"
    
    # Raison hospitalisation
    match_raison_hosp = re.search(r"Si\s+oui.*?précisez\s+pour\s+quelle\s+raison\s*[:•]\s*([^\n\r]+)", texte, re.IGNORECASE | re.DOTALL)
    data["historique_medical"]["raison_hospitalisation"] = match_raison_hosp.group(1).strip() if match_raison_hosp else ""
    
    # === SECTION 2: SANTÉ ACTUELLE ===
    match_malade = re.search(r"malade\s+au\s+moment\s+de\s+la\s+souscription\??\s*(Oui|Non|OUI|NON)", texte, re.IGNORECASE)
    data["sante_actuelle"]["malade_actuellement"] = match_malade.group(1).strip() if match_malade else "Non"
    
    match_souffrance = re.search(r"Si\s+oui.*?précisez\s+de\s+quoi\s+souffrez-vous\??\s*[:•]\s*([^\n\r]+)", texte, re.IGNORECASE | re.DOTALL)
    data["sante_actuelle"]["maladie_actuelle"] = match_souffrance.group(1).strip() if match_souffrance else ""
    
    match_symptomes = re.search(r"symptômes\s+persistants\??\s*(Oui|Non|OUI|NON)", texte, re.IGNORECASE)
    data["sante_actuelle"]["symptomes_persistants"] = match_symptomes.group(1).strip() if match_symptomes else "Non"
    
    match_symptomes_details = re.search(r"Si\s+oui.*?précisez\s*[:•]\s*([^\n\r]+)", texte, re.IGNORECASE | re.DOTALL)
    data["sante_actuelle"]["symptomes_details"] = match_symptomes_details.group(1).strip() if match_symptomes_details else ""
    
    match_medecin = re.search(r"médecin\s+traitant\s*[:•]\s*(Oui|Non|OUI|NON)", texte, re.IGNORECASE)
    data["sante_actuelle"]["medecin_traitant"] = match_medecin.group(1).strip() if match_medecin else "Non"
    
    match_nom_medecin = re.search(r"son\s+nom\s*[:•]\s*([^\n\r]+)", texte, re.IGNORECASE)
    data["sante_actuelle"]["nom_medecin"] = match_nom_medecin.group(1).strip() if match_nom_medecin else ""
    
    match_specialite = re.search(r"Spécialité\s*[:•]\s*([^\n\r]+)", texte, re.IGNORECASE)
    data["sante_actuelle"]["specialite_medecin"] = match_specialite.group(1).strip() if match_specialite else ""
    
    match_tel_medecin = re.search(r"Téléphone\s*[:•]\s*([^\n\r]+)", texte, re.IGNORECASE)
    data["sante_actuelle"]["telephone_medecin"] = match_tel_medecin.group(1).strip() if match_tel_medecin else ""
    
    # === SECTION 3: MODE DE VIE ===
    match_fumeur = re.search(r"Fumez-vous\??\s*(Oui|Non|OUI|NON)", texte, re.IGNORECASE)
    data["mode_vie"]["fumeur"] = match_fumeur.group(1).strip() if match_fumeur else "Non"
    
    match_cigarettes = re.search(r"Si\s+oui.*?combien\s+de\s+cigarettes\s+par\s+jour\??\s*[:•]\s*(\d+)", texte, re.IGNORECASE | re.DOTALL)
    data["mode_vie"]["nb_cigarettes"] = match_cigarettes.group(1).strip() if match_cigarettes else "0"
    
    match_alcool = re.search(r"Consommez-vous\s+de\s+l['']alcool\??\s*(Oui|Non|OUI|NON)", texte, re.IGNORECASE)
    data["mode_vie"]["alcool"] = match_alcool.group(1).strip() if match_alcool else "Non"
    
    match_freq_alcool = re.search(r"Si\s+oui.*?à\s+quelle\s+fréquence\??\s*[:•]\s*([^\n\r]+)", texte, re.IGNORECASE | re.DOTALL)
    if match_freq_alcool:
        freq_text = match_freq_alcool.group(1).lower()
        if "quotidien" in freq_text:
            data["mode_vie"]["frequence_alcool"] = "Quotidiennement"
        elif "régulier" in freq_text or "1 à 2" in freq_text:
            data["mode_vie"]["frequence_alcool"] = "Régulièrement (1 à 2 fois par semaine)"
        else:
            data["mode_vie"]["frequence_alcool"] = "Occasionnellement"
    else:
        data["mode_vie"]["frequence_alcool"] = ""
    
    match_activite = re.search(r"activité\s+physique\s+régulièrement\??\s*(Oui|Non|OUI|NON)", texte, re.IGNORECASE)
    data["mode_vie"]["activite_physique"] = match_activite.group(1).strip() if match_activite else "Non"
    
    match_activite_details = re.search(r"Si\s+oui.*?laquelle\s+et\s+à\s+quelle\s+fréquence\??\s*[:•]\s*([^\n\r]+)", texte, re.IGNORECASE | re.DOTALL)
    data["mode_vie"]["activite_details"] = match_activite_details.group(1).strip() if match_activite_details else ""
    
    # === SECTION 4: ALLERGIES ===
    match_allergie = re.search(r"allergique\s+à\s+certains\s+médicaments.*?\??\s*(Oui|Non|OUI|NON)", texte, re.IGNORECASE)
    data["allergies"]["presence"] = match_allergie.group(1).strip() if match_allergie else "Non"
    
    match_allergie_details = re.search(r"Si\s+oui.*?précisez\s*[:•]\s*([^\n\r]+)", texte, re.IGNORECASE | re.DOTALL)
    data["allergies"]["details"] = match_allergie_details.group(1).strip() if match_allergie_details else ""
    
    # === SECTION 5: SANTÉ MENTALE ===
    match_mental = re.search(r"trouble\s+mental\s+ou\s+émotionnel\??\s*(Oui|Non|OUI|NON)", texte, re.IGNORECASE)
    data["sante_mentale"]["trouble_mental"] = match_mental.group(1).strip() if match_mental else "Non"
    
    match_mental_details = re.search(r"Si\s+oui.*?précisez\s*[:•]\s*([^\n\r]+)", texte, re.IGNORECASE | re.DOTALL)
    data["sante_mentale"]["details"] = match_mental_details.group(1).strip() if match_mental_details else ""
    
    return data

# --- Calcul du score de cohérence amélioré avec détection de fraude ---
def calculer_score_coherence(infos_personnelles, infos_sante):
    """
    Calcule un score de cohérence entre les différentes réponses
    Détecte les incohérences et signaux de fraude potentielle
    """
    incohérences = []
    signaux_fraude = []
    score = 100.0
    
    # ═══════════════════════════════════════════════════════════
    # VÉRIFICATIONS MÉDICALES - INCOHÉRENCES
    # ═══════════════════════════════════════════════════════════
    
    # Vérification 1: "Aucune maladie" mais d'autres maladies cochées
    if infos_sante["historique_medical"].get("Aucune de ces maladies", False):
        autres_maladies = [
            "Hypertension artérielle",
            "Diabète",
            "Maladies cardiaques",
            "Maladies respiratoires",
            "Maladies neurologiques",
            "Maladies chroniques"
        ]
        for maladie in autres_maladies:
            if infos_sante["historique_medical"].get(maladie, False):
                incohérences.append(f"Incohérence: 'Aucune maladie' mais '{maladie}' cochée")
                signaux_fraude.append(f"⚠️ FRAUDE POTENTIELLE: Contradiction majeure - '{maladie}' déclarée alors que 'Aucune maladie' est coché")
                score -= 20
    
    # Vérification 2: Malade actuellement mais pas de symptômes
    if infos_sante["sante_actuelle"].get("malade_actuellement") == "Oui":
        if infos_sante["sante_actuelle"].get("symptomes_persistants") == "Non":
            incohérences.append("Incohérence: Malade actuellement mais pas de symptômes persistants")
            signaux_fraude.append("⚠️ FRAUDE POTENTIELLE: Maladie actuelle déclarée sans symptômes")
            score -= 15
    
    # Vérification 3: Traitement régulier mais aucune maladie déclarée
    if infos_sante["historique_medical"].get("traitement_regulier") == "Oui":
        type_traitement = infos_sante["historique_medical"].get("type_traitement", "").strip()
        if not any([
            infos_sante["historique_medical"].get("Hypertension artérielle", False),
            infos_sante["historique_medical"].get("Diabète", False),
            infos_sante["historique_medical"].get("Maladies cardiaques", False),
            infos_sante["historique_medical"].get("Maladies respiratoires", False),
            infos_sante["historique_medical"].get("Maladies neurologiques", False),
            infos_sante["historique_medical"].get("Maladies chroniques", False)
        ]) and not type_traitement:
            incohérences.append("Incohérence: Traitement régulier mais aucune maladie déclarée")
            signaux_fraude.append("⚠️ FRAUDE POTENTIELLE: Traitement médical sans maladie déclarée")
            score -= 15
    
    # Vérification 4: Hospitalisation récente mais aucune raison
    if infos_sante["historique_medical"].get("hospitalisation_recente") == "Oui":
        raison = infos_sante["historique_medical"].get("raison_hospitalisation", "").strip()
        if not raison:
            incohérences.append("Incohérence: Hospitalisation récente mais raison non précisée")
            signaux_fraude.append("⚠️ FRAUDE POTENTIELLE: Hospitalisation déclarée sans justification")
            score -= 10
    
    # ═══════════════════════════════════════════════════════════
    # VÉRIFICATIONS MODE DE VIE - INCOHÉRENCES
    # ═══════════════════════════════════════════════════════════
    
    # Vérification 5: Fumeur mais nombre de cigarettes = 0 ou invalide
    if infos_sante["mode_vie"].get("fumeur") == "Oui":
        nb_cig = infos_sante["mode_vie"].get("nb_cigarettes", "0")
        try:
            nb_cig_int = int(nb_cig) if nb_cig else 0
            if nb_cig_int == 0:
                incohérences.append("Incohérence: Fumeur déclaré mais nombre de cigarettes non précisé")
                signaux_fraude.append("⚠️ FRAUDE POTENTIELLE: Fumeur déclaré sans précision")
                score -= 8
            elif nb_cig_int > 60:  # Suspicion si > 60 cigarettes/jour
                incohérences.append(f"Incohérence: Nombre de cigarettes anormalement élevé ({nb_cig_int}/jour)")
                signaux_fraude.append(f"⚠️ FRAUDE POTENTIELLE: Nombre de cigarettes suspect ({nb_cig_int}/jour)")
            score -= 5
        except:
            incohérences.append("Incohérence: Fumeur déclaré mais nombre de cigarettes invalide")
            score -= 8
    
    # Vérification 6: Alcool mais fréquence non précisée
    if infos_sante["mode_vie"].get("alcool") == "Oui":
        if not infos_sante["mode_vie"].get("frequence_alcool", ""):
            incohérences.append("Incohérence: Consommation d'alcool déclarée mais fréquence non précisée")
            score -= 5
    
    # ═══════════════════════════════════════════════════════════
    # VÉRIFICATIONS SANTÉ ACTUELLE - INCOHÉRENCES
    # ═══════════════════════════════════════════════════════════
    
    # Vérification 7: Symptômes persistants mais pas de maladie actuelle
    if infos_sante["sante_actuelle"].get("symptomes_persistants") == "Oui":
        symptomes_details = infos_sante["sante_actuelle"].get("symptomes_details", "").strip()
        if not symptomes_details:
            incohérences.append("Incohérence: Symptômes persistants déclarés mais détails non fournis")
            score -= 8
    
    # Vérification 8: Médecin traitant mais informations manquantes
    if infos_sante["sante_actuelle"].get("medecin_traitant") == "Oui":
        nom_medecin = infos_sante["sante_actuelle"].get("nom_medecin", "").strip()
        if not nom_medecin:
            incohérences.append("Incohérence: Médecin traitant déclaré mais nom non fourni")
            score -= 5
    
    # ═══════════════════════════════════════════════════════════
    # VÉRIFICATIONS ALLERGIES - INCOHÉRENCES
    # ═══════════════════════════════════════════════════════════
    
    # Vérification 9: Allergies déclarées mais détails manquants
    if infos_sante["allergies"].get("presence") == "Oui":
        details_allergie = infos_sante["allergies"].get("details", "").strip()
        if not details_allergie:
            incohérences.append("Incohérence: Allergies déclarées mais détails non fournis")
            score -= 5
    
    # ═══════════════════════════════════════════════════════════
    # VÉRIFICATIONS SANTÉ MENTALE - INCOHÉRENCES
    # ═══════════════════════════════════════════════════════════
    
    # Vérification 10: Trouble mental déclaré mais détails manquants
    if infos_sante["sante_mentale"].get("trouble_mental") == "Oui":
        details_mental = infos_sante["sante_mentale"].get("details", "").strip()
        if not details_mental:
            incohérences.append("Incohérence: Trouble mental déclaré mais détails non fournis")
            score -= 8
    
    # ═══════════════════════════════════════════════════════════
    # VÉRIFICATIONS INFORMATIONS PERSONNELLES - FRAUDE
    # ═══════════════════════════════════════════════════════════
    
    # Vérification 11: Email invalide
    email = infos_personnelles.get("email", "").strip()
    if email and "@" in email:
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            incohérences.append(f"Incohérence: Format d'email invalide ({email})")
            signaux_fraude.append(f"⚠️ FRAUDE POTENTIELLE: Email invalide ({email})")
            score -= 5
    
    # Vérification 12: Téléphone invalide (trop court)
    telephone = infos_personnelles.get("telephone", "").strip()
    if telephone:
        digits_only = re.sub(r'\D', '', telephone)
        if len(digits_only) < 8:
            incohérences.append(f"Incohérence: Numéro de téléphone suspect ({telephone})")
            signaux_fraude.append(f"⚠️ FRAUDE POTENTIELLE: Numéro de téléphone invalide ({telephone})")
            score -= 5
    
    # Vérification 13: Date de naissance invalide
    date_naissance = infos_personnelles.get("date_naissance", "").strip()
    if date_naissance:
        # Vérifier si c'est une date valide
        if not re.match(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', date_naissance):
            incohérences.append(f"Incohérence: Format de date de naissance invalide ({date_naissance})")
            score -= 5
    
    score = max(0.0, min(100.0, score))
    return round(score, 2), incohérences, signaux_fraude

# --- Calcul du score de confiance global ---
def calculer_score_confiance(infos_personnelles, infos_sante, confiance_ocr):
    """
    Calcule un score de confiance global sur la qualité de l'extraction
    """
    score = 0.0
    poids_total = 0.0
    
    # Poids OCR (30%)
    poids_ocr = 0.3
    score += confiance_ocr * poids_ocr
    poids_total += poids_ocr
    
    # Poids informations personnelles (30%)
    champs_perso_importants = ["nom", "prenom", "date_naissance", "email", "telephone"]
    remplis_perso = sum(1 for champ in champs_perso_importants if infos_personnelles.get(champ, "").strip())
    score_perso = remplis_perso / len(champs_perso_importants) if champs_perso_importants else 0
    poids_perso = 0.3
    score += score_perso * poids_perso
    poids_total += poids_perso
    
    # Poids informations santé (40%)
    champs_sante_importants = [
        "traitement_regulier",
        "hospitalisation_recente",
        "malade_actuellement",
        "symptomes_persistants",
        "fumeur",
        "alcool",
        "activite_physique",
        "presence"  # allergies
    ]
    remplis_sante = 0
    for champ in champs_sante_importants:
        if champ == "presence":
            if infos_sante.get("allergies", {}).get("presence", "") != "":
                remplis_sante += 1
        elif champ in ["traitement_regulier", "hospitalisation_recente", "malade_actuellement", "symptomes_persistants"]:
            if infos_sante.get("historique_medical", {}).get(champ, "") != "" or \
               infos_sante.get("sante_actuelle", {}).get(champ, "") != "":
                remplis_sante += 1
        else:
            if infos_sante.get("mode_vie", {}).get(champ, "") != "":
                remplis_sante += 1
    
    score_sante = remplis_sante / len(champs_sante_importants) if champs_sante_importants else 0
    poids_sante = 0.4
    score += score_sante * poids_sante
    poids_total += poids_sante
    
    return round(score, 2)

# --- Calcul de la probabilité de fraude ---
def calculer_probabilite_fraude(signaux_fraude, incohérences, score_coherence, confiance_ocr):
    """
    Calcule la probabilité que la demande soit frauduleuse
    """
    probabilite_fraude = 0.0
    
    # Base: Score de cohérence (plus bas = plus de fraude)
    if score_coherence < 50:
        probabilite_fraude += 0.40
    elif score_coherence < 70:
        probabilite_fraude += 0.25
    elif score_coherence < 85:
        probabilite_fraude += 0.10
    
    # Signaux de fraude explicites
    probabilite_fraude += len(signaux_fraude) * 0.15
    
    # Incohérences multiples
    if len(incohérences) >= 5:
        probabilite_fraude += 0.20
    elif len(incohérences) >= 3:
        probabilite_fraude += 0.10
    
    # Confiance OCR faible (document peut être falsifié)
    if confiance_ocr < 50:
        probabilite_fraude += 0.10
    
    # Normaliser entre 0 et 1
    probabilite_fraude = min(1.0, probabilite_fraude)
    
    # Niveau de fraude
    if probabilite_fraude >= 0.7:
        niveau_fraude = "TRÈS ÉLEVÉ"
    elif probabilite_fraude >= 0.5:
        niveau_fraude = "ÉLEVÉ"
    elif probabilite_fraude >= 0.3:
        niveau_fraude = "MODÉRÉ"
    else:
        niveau_fraude = "FAIBLE"
    
    return round(probabilite_fraude, 3), niveau_fraude

# --- Calcul de la probabilité de confiance pour l'assureur ---
def calculer_probabilite_confiance_assureur(score_coherence, confiance_ocr, signaux_fraude, 
                                           probabilite_fraude, probabilite_acceptation):
    """
    Calcule la probabilité que l'assureur peut faire confiance à cette demande
    C'est différent de la probabilité d'acceptation (qui dépend du risque médical)
    """
    # Base: Probabilité d'acceptation (risque médical)
    confiance = probabilite_acceptation * 0.40
    
    # Score de cohérence (30%)
    confiance += (score_coherence / 100) * 0.30
    
    # Confiance OCR (20%)
    confiance += (confiance_ocr / 100) * 0.20
    
    # Pénalité pour fraude (10%)
    confiance -= probabilite_fraude * 0.10
    
    # Normaliser entre 0 et 1
    confiance = max(0.0, min(1.0, confiance))
    
    # Niveau de confiance
    if confiance >= 0.8:
        niveau_confiance = "TRÈS ÉLEVÉE"
    elif confiance >= 0.6:
        niveau_confiance = "ÉLEVÉE"
    elif confiance >= 0.4:
        niveau_confiance = "MODÉRÉE"
    elif confiance >= 0.2:
        niveau_confiance = "FAIBLE"
    else:
        niveau_confiance = "TRÈS FAIBLE"
    
    return round(confiance, 3), niveau_confiance

# --- Calcul du risque et probabilité d'acceptation ---
def calculer_risque_et_acceptation(infos_sante):
    """
    Calcule le niveau de risque et la probabilité d'acceptation
    """
    score_risque = 0.0
    facteurs_risque = []
    
    # Facteurs de risque médicaux (poids élevé)
    if infos_sante["historique_medical"].get("Hypertension artérielle", False):
        score_risque += 0.15
        facteurs_risque.append("Hypertension artérielle")
    
    if infos_sante["historique_medical"].get("Diabète", False):
        score_risque += 0.20
        facteurs_risque.append("Diabète")
    
    if infos_sante["historique_medical"].get("Maladies cardiaques", False):
        score_risque += 0.25
        facteurs_risque.append("Maladies cardiaques")
    
    if infos_sante["historique_medical"].get("Maladies respiratoires", False):
        score_risque += 0.15
        facteurs_risque.append("Maladies respiratoires")
    
    if infos_sante["historique_medical"].get("Maladies neurologiques", False):
        score_risque += 0.20
        facteurs_risque.append("Maladies neurologiques")
    
    if infos_sante["historique_medical"].get("Maladies chroniques", False):
        score_risque += 0.20
        facteurs_risque.append("Maladies chroniques")
    
    if infos_sante["historique_medical"].get("hospitalisation_recente") == "Oui":
        score_risque += 0.15
        facteurs_risque.append("Hospitalisation récente")
    
    if infos_sante["sante_actuelle"].get("malade_actuellement") == "Oui":
        score_risque += 0.20
        facteurs_risque.append("Maladie actuelle")
    
    if infos_sante["sante_actuelle"].get("symptomes_persistants") == "Oui":
        score_risque += 0.15
        facteurs_risque.append("Symptômes persistants")
    
    # Facteurs de risque mode de vie
    if infos_sante["mode_vie"].get("fumeur") == "Oui":
        nb_cig = int(infos_sante["mode_vie"].get("nb_cigarettes", "0") or "0")
        if nb_cig > 20:
            score_risque += 0.20
            facteurs_risque.append(f"Fumeur intensif ({nb_cig} cigarettes/jour)")
        elif nb_cig > 0:
            score_risque += 0.10
            facteurs_risque.append(f"Fumeur ({nb_cig} cigarettes/jour)")
    
    if infos_sante["mode_vie"].get("alcool") == "Oui":
        freq = infos_sante["mode_vie"].get("frequence_alcool", "")
        if "Quotidien" in freq:
            score_risque += 0.15
            facteurs_risque.append("Consommation d'alcool quotidienne")
        elif "Régulier" in freq:
            score_risque += 0.10
            facteurs_risque.append("Consommation d'alcool régulière")
        else:
            score_risque += 0.05
            facteurs_risque.append("Consommation d'alcool occasionnelle")
    
    # Facteurs positifs (réduction du risque)
    if infos_sante["mode_vie"].get("activite_physique") == "Oui":
        score_risque -= 0.10
        facteurs_risque.append("Activité physique régulière (facteur positif)")
    
    if infos_sante["sante_mentale"].get("trouble_mental") == "Oui":
        score_risque += 0.10
        facteurs_risque.append("Trouble mental diagnostiqué")
    
    # Normaliser le score entre 0 et 1
    score_risque = max(0.0, min(1.0, score_risque))
    
    # Probabilité d'acceptation (inverse du risque)
    probabilite_acceptation = round(1.0 - score_risque, 2)
    
    # Niveau de risque
    if score_risque >= 0.7:
        niveau_risque = "Très élevé"
    elif score_risque >= 0.5:
        niveau_risque = "Élevé"
    elif score_risque >= 0.3:
        niveau_risque = "Modéré"
    else:
        niveau_risque = "Faible"
    
    return round(score_risque, 2), probabilite_acceptation, niveau_risque, facteurs_risque

# --- Génération de l'avis et commentaire amélioré ---
def generer_avis_et_commentaire(score_risque, probabilite_acceptation, niveau_risque, facteurs_risque, 
                                 score_coherence, incohérences, infos_sante, signaux_fraude, 
                                 probabilite_fraude, probabilite_confiance_assureur,
                                 verification_document=None):
    """
    Génère un avis détaillé et un commentaire sur la demande avec toutes les métriques
    """
    # Avis basé sur la probabilité d'acceptation ET la probabilité de fraude
    if probabilite_fraude >= 0.5:
        avis = "REJET RECOMMANDÉ (FRAUDE SUSPECTÉE)"
    elif probabilite_acceptation >= 0.7 and probabilite_fraude < 0.3:
        avis = "FAVORABLE"
    elif probabilite_acceptation >= 0.5:
        avis = "RÉSERVÉ"
    elif probabilite_acceptation >= 0.3:
        avis = "DÉFAVORABLE"
    else:
        avis = "TRÈS DÉFAVORABLE"
    
    # Commentaire détaillé
    commentaire_parts = []
    
    commentaire_parts.append("═══════════════════════════════════════════════════════")
    commentaire_parts.append("📊 ANALYSE COMPLÈTE DE LA DEMANDE DE SOUSCRIPTION")
    commentaire_parts.append("═══════════════════════════════════════════════════════")
    
    # Métriques principales
    commentaire_parts.append(f"\n🎯 MÉTRIQUES PRINCIPALES:")
    commentaire_parts.append(f"  • Probabilité d'acceptation: {probabilite_acceptation:.1%}")
    commentaire_parts.append(f"  • Probabilité de confiance (assureur): {probabilite_confiance_assureur:.1%}")
    commentaire_parts.append(f"  • Probabilité de fraude: {probabilite_fraude:.1%}")
    commentaire_parts.append(f"  • Score de risque médical: {score_risque:.1%}")
    commentaire_parts.append(f"  • Score de cohérence: {score_coherence:.1f}/100")
    commentaire_parts.append(f"  • Niveau de risque: {niveau_risque}")
    
    # Vérifications du document
    if verification_document:
        commentaire_parts.append(f"\n📄 VÉRIFICATION DU DOCUMENT:")
        commentaire_parts.append(f"  • Type de document: {verification_document.get('type_document', 'N/A')}")
        
        dates = verification_document.get("dates_document", {})
        if dates.get("date_expiration"):
            commentaire_parts.append(f"  • Date d'expiration: {dates.get('date_expiration')}")
            commentaire_parts.append(f"  • {verification_document.get('message_expiration', '')}")
        
        if verification_document.get("besoin_nouveau_fichier"):
            commentaire_parts.append(f"\n  ⚠️ {verification_document.get('message_qualite', '')}")
        
        if verification_document.get("doit_verifier") and not verification_document.get("est_complet"):
            commentaire_parts.append(f"\n  ⚠️ {verification_document.get('message_completude', '')}")
        
        if not verification_document.get("est_coherent_documents"):
            commentaire_parts.append(f"\n  🚨 {verification_document.get('message_coherence', '')}")
    
    # Signaux de fraude
    if signaux_fraude:
        commentaire_parts.append(f"\n🚨 SIGNAUX DE FRAUDE DÉTECTÉS ({len(signaux_fraude)}):")
        for signal in signaux_fraude[:5]:  # Limiter à 5 signaux
            commentaire_parts.append(f"  {signal}")
        if len(signaux_fraude) > 5:
            commentaire_parts.append(f"  ... et {len(signaux_fraude) - 5} autre(s) signal(aux)")
    
    # Incohérences
    if incohérences:
        commentaire_parts.append(f"\n⚠️ INCOHÉRENCES DÉTECTÉES ({len(incohérences)}):")
        for inc in incohérences[:5]:  # Limiter à 5
            commentaire_parts.append(f"  • {inc}")
        if len(incohérences) > 5:
            commentaire_parts.append(f"  ... et {len(incohérences) - 5} autre(s) incohérence(s)")
    
    # Facteurs de risque
    if facteurs_risque:
        commentaire_parts.append(f"\n🔍 FACTEURS DE RISQUE MÉDICAUX ({len(facteurs_risque)}):")
        for facteur in facteurs_risque[:8]:  # Limiter à 8 facteurs
            commentaire_parts.append(f"  • {facteur}")
        if len(facteurs_risque) > 8:
            commentaire_parts.append(f"  ... et {len(facteurs_risque) - 8} autre(s) facteur(s)")
    
    # Recommandations
    commentaire_parts.append(f"\n💡 RECOMMANDATIONS POUR L'ASSUREUR:")
    if probabilite_fraude >= 0.5:
        commentaire_parts.append("  ⛔ REJET RECOMMANDÉ - Fraude suspectée")
        commentaire_parts.append("  • Vérification approfondie requise")
        commentaire_parts.append("  • Contrôle des documents originaux nécessaire")
        commentaire_parts.append("  • Investigation supplémentaire recommandée")
    elif probabilite_acceptation < 0.3:
        commentaire_parts.append("  ⚠️ REJET RECOMMANDÉ - Risque médical trop élevé")
        commentaire_parts.append("  • Examen médical approfondi requis")
        commentaire_parts.append("  • Évaluation par un médecin conseil obligatoire")
        commentaire_parts.append("  • Vérification des antécédents médicaux nécessaire")
    elif probabilite_acceptation < 0.5:
        commentaire_parts.append("  ⚠️ ACCEPTATION SOUS CONDITIONS")
        commentaire_parts.append("  • Examen médical complémentaire recommandé")
        commentaire_parts.append("  • Vérification des informations médicales requise")
        commentaire_parts.append("  • Surprime possible selon l'évaluation")
    elif probabilite_acceptation < 0.7:
        commentaire_parts.append("  ✅ ACCEPTATION AVEC PRÉCAUTIONS")
        commentaire_parts.append("  • Vérification complémentaire recommandée")
        commentaire_parts.append("  • Conditions standard applicables")
    else:
        commentaire_parts.append("  ✅ ACCEPTATION STANDARD")
        commentaire_parts.append("  • Demande conforme aux critères standards")
        commentaire_parts.append("  • Traitement standard recommandé")
        commentaire_parts.append("  • Aucune vérification supplémentaire nécessaire")
    
    commentaire = "\n".join(commentaire_parts)
    
    return avis, commentaire

# --- Détection du type de document ---
def detecter_type_document(texte, filepath):
    """
    Détecte le type de document (Passeport, CNI, Carte d'identité, etc.)
    """
    texte_lower = texte.lower()
    nom_fichier = os.path.basename(filepath).lower()
    
    type_doc = "Document inconnu"
    
    # Détection par mots-clés
    if any(mot in texte_lower for mot in ["passeport", "passport", "pass no", "passport no"]):
        type_doc = "Passeport"
    elif any(mot in texte_lower for mot in ["carte nationale", "cni", "carte d'identité", "national identity"]):
        type_doc = "CNI / Carte d'identité"
    elif any(mot in texte_lower for mot in ["permis de conduire", "driving license", "permis"]):
        type_doc = "Permis de conduire"
    elif any(mot in texte_lower for mot in ["attestation", "certificat"]):
        type_doc = "Attestation / Certificat"
    elif "passport" in nom_fichier:
        type_doc = "Passeport"
    elif "cni" in nom_fichier or "identite" in nom_fichier:
        type_doc = "CNI / Carte d'identité"
    
    return type_doc

# --- Extraction des dates de document (délivrance et expiration) ---
def extraire_dates_document(texte):
    """
    Extrait les dates de délivrance/émission et d'expiration du document
    """
    dates = {
        "date_delivrance": None,
        "date_expiration": None,
        "date_emission": None
    }
    
    # Patterns pour date de délivrance/émission
    patterns_delivrance = [
        r"Date\s+de\s+délivrance\s*[:•]\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"Date\s+délivrance\s*[:•]\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"Délivré\s+le\s*[:•]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"Date\s+d['']émission\s*[:•]\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"Date\s+émission\s*[:•]\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"Émis\s+le\s*[:•]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"Issued\s+on\s*[:•]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"Issue\s+date\s*[:•]\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
    ]
    
    # Patterns pour date d'expiration
    patterns_expiration = [
        r"Date\s+d['']expiration\s*[:•]\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"Date\s+expiration\s*[:•]\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"Expire\s+le\s*[:•]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"Expires\s+on\s*[:•]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"Expiry\s+date\s*[:•]\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"Valid\s+until\s*[:•]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"Valable\s+jusqu['']au\s*[:•]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
    ]
    
    # Chercher date de délivrance
    for pattern in patterns_delivrance:
        match = re.search(pattern, texte, re.IGNORECASE)
        if match:
            dates["date_delivrance"] = match.group(1).strip()
            dates["date_emission"] = match.group(1).strip()  # Même chose
            break
    
    # Chercher date d'expiration
    for pattern in patterns_expiration:
        match = re.search(pattern, texte, re.IGNORECASE)
        if match:
            dates["date_expiration"] = match.group(1).strip()
            break
    
    return dates

# --- Vérifier si le document est expiré ---
def verifier_expiration_document(date_expiration_str):
    """
    Vérifie si la date d'expiration est passée
    Retourne (est_expire, jours_restants, message)
    """
    if not date_expiration_str:
        return False, None, "Date d'expiration non trouvée"
    
    try:
        # Parser la date (formats: DD/MM/YYYY, DD-MM-YYYY, etc.)
        date_exp = None
        for sep in ["/", "-", "."]:
            parts = date_expiration_str.split(sep)
            if len(parts) == 3:
                try:
                    if len(parts[2]) == 2:
                        parts[2] = "20" + parts[2] if int(parts[2]) < 50 else "19" + parts[2]
                    date_exp = date(int(parts[2]), int(parts[1]), int(parts[0]))
                    break
                except:
                    continue
        
        if not date_exp:
            return False, None, f"Format de date invalide: {date_expiration_str}"
        
        # Comparer avec la date actuelle
        aujourdhui = date.today()
        jours_restants = (date_exp - aujourdhui).days
        
        if jours_restants < 0:
            return True, jours_restants, f"⚠️ FRAUDE: Document expiré depuis {abs(jours_restants)} jour(s) (expiré le {date_expiration_str})"
        elif jours_restants < 30:
            return False, jours_restants, f"⚠️ ATTENTION: Document expire dans {jours_restants} jour(s)"
        else:
            return False, jours_restants, f"✅ Document valide jusqu'au {date_expiration_str} ({jours_restants} jours restants)"
            
    except Exception as e:
        return False, None, f"Erreur lors de la vérification de la date: {str(e)}"

# --- Vérifier la qualité du document (flou, illisible) ---
def verifier_qualite_document(confiance_ocr, texte, filepath):
    """
    Vérifie si le document est de qualité suffisante (pas trop flou)
    Retourne (qualite_ok, message, besoin_nouveau_fichier)
    """
    messages = []
    besoin_nouveau = False
    
    # Vérification 1: Confiance OCR
    if confiance_ocr < 0.3:  # Très faible confiance
        messages.append("🚨 DOCUMENT TRÈS FLOU: Confiance OCR très faible (< 30%)")
        besoin_nouveau = True
    elif confiance_ocr < 0.5:  # Faible confiance
        messages.append("⚠️ DOCUMENT FLOU: Confiance OCR faible (< 50%)")
        besoin_nouveau = True
    elif confiance_ocr < 0.7:
        messages.append("⚠️ Qualité du document moyenne (confiance OCR < 70%)")
    
    # Vérification 2: Longueur du texte extrait
    if len(texte.strip()) < 50:
        messages.append("🚨 DOCUMENT ILLISIBLE: Très peu de texte extrait (< 50 caractères)")
        besoin_nouveau = True
    elif len(texte.strip()) < 100:
        messages.append("⚠️ DOCUMENT DIFFICILE À LIRE: Peu de texte extrait (< 100 caractères)")
        besoin_nouveau = True
    
    # Vérification 3: Ratio de caractères valides
    caracteres_valides = len(re.findall(r'[a-zA-Z0-9\s]', texte))
    total_caracteres = len(texte)
    if total_caracteres > 0:
        ratio = caracteres_valides / total_caracteres
        if ratio < 0.5:
            messages.append("🚨 DOCUMENT CORROMPU: Beaucoup de caractères invalides")
            besoin_nouveau = True
    
    if not messages:
        messages.append("✅ Qualité du document acceptable")
    
    message_final = "\n".join(messages)
    
    if besoin_nouveau:
        message_final += "\n\n📋 ACTION REQUISE: Veuillez fournir un nouveau fichier/document de meilleure qualité"
    
    return not besoin_nouveau, message_final, besoin_nouveau

# --- Vérifier la complétude des informations ---
def verifier_completude_informations(infos_personnelles, infos_sante, type_document):
    """
    Vérifie si les informations sont complètes
    Ne signale "document à vérifier" que si vraiment incomplet
    Retourne (est_complet, champs_manquants, message, doit_verifier)
    """
    champs_manquants = []
    champs_obligatoires = ["nom", "prenom", "date_naissance"]
    
    # Vérifier les champs personnels obligatoires
    champs_perso_remplis = 0
    for champ in champs_obligatoires:
        valeur = infos_personnelles.get(champ, "").strip()
        if not valeur:
            champs_manquants.append(champ)
        else:
            champs_perso_remplis += 1
    
    # Vérifier les informations santé (questionnaire médical)
    champs_sante_importants = [
        ("historique_medical", "traitement_regulier"),
        ("historique_medical", "hospitalisation_recente"),
        ("sante_actuelle", "malade_actuellement"),
        ("sante_actuelle", "symptomes_persistants"),
        ("mode_vie", "fumeur"),
        ("mode_vie", "alcool"),
        ("mode_vie", "activite_physique")
    ]
    
    champs_sante_remplis = 0
    for section, champ in champs_sante_importants:
        if infos_sante.get(section, {}).get(champ, ""):
            champs_sante_remplis += 1
    
    # Logique simplifiée : vérifier questionnaire médical + infos personnelles
    # (Les informations de voyage ne sont plus requises)
    a_questionnaire_medical = champs_sante_remplis >= 2
    a_infos_personnelles = champs_perso_remplis >= 2  # Au moins nom et prénom
    
    # Si on a questionnaire médical + infos perso → OK
    if a_questionnaire_medical and a_infos_personnelles:
        return True, [], "✅ Informations complètes (questionnaire médical + infos personnelles)", False
    
    # Si on a seulement les infos personnelles (sans questionnaire médical)
    if a_infos_personnelles and not a_questionnaire_medical:
        message = f"⚠️ DOCUMENT À VÉRIFIER: Seulement les informations personnelles trouvées. Questionnaire médical manquant."
        return False, champs_manquants + ["questionnaire_medical"], message, True
    
    # Si on a seulement le questionnaire médical (sans infos personnelles)
    if a_questionnaire_medical and not a_infos_personnelles:
        message = "⚠️ DOCUMENT À VÉRIFIER: Seulement le questionnaire médical trouvé. Informations personnelles manquantes."
        return False, champs_manquants, message, True
    
    # Cas par défaut pour documents d'identité
    if type_document in ["Passeport", "CNI / Carte d'identité"]:
        if champs_perso_remplis < 2:
            message = f"⚠️ DOCUMENT À VÉRIFIER: Informations personnelles incomplètes (champs manquants: {', '.join(champs_manquants)})"
            return False, champs_manquants, message, True
        else:
            return True, [], "✅ Informations complètes pour document d'identité", False
    
    # Si vraiment rien
    message = "⚠️ DOCUMENT À VÉRIFIER: Très peu d'informations trouvées."
    return False, champs_manquants, message, True

# --- Vérifier la cohérence entre documents (fraude si nom/sexe différent) ---
def verifier_coherence_documents(infos_personnelles_actuelles, infos_client_stockees=None):
    """
    Vérifie si les informations du document actuel sont cohérentes avec celles stockées
    Si nom ou sexe différent → signal de fraude
    Retourne (est_coherent, signaux_fraude, message)
    """
    signaux_fraude = []
    
    if not infos_client_stockees:
        # Premier document, pas de comparaison possible
        return True, [], "Premier document analysé"
    
    nom_actuel = infos_personnelles_actuelles.get("nom", "").strip().upper()
    prenom_actuel = infos_personnelles_actuelles.get("prenom", "").strip().upper()
    sexe_actuel = infos_personnelles_actuelles.get("sexe", "").strip().upper()
    
    nom_stocke = infos_client_stockees.get("nom", "").strip().upper()
    prenom_stocke = infos_client_stockees.get("prenom", "").strip().upper()
    sexe_stocke = infos_client_stockees.get("sexe", "").strip().upper()
    
    # Normaliser le sexe
    def normaliser_sexe(sexe):
        if not sexe:
            return ""
        sexe = sexe.upper()
        if sexe in ["M", "MASCULIN", "HOMME", "H", "MALE"]:
            return "M"
        elif sexe in ["F", "FÉMININ", "FEMININ", "FEMME", "FEMALE"]:
            return "F"
        return sexe
    
    sexe_actuel_norm = normaliser_sexe(sexe_actuel)
    sexe_stocke_norm = normaliser_sexe(sexe_stocke)
    
    # Vérifier le nom
    if nom_actuel and nom_stocke and nom_actuel != nom_stocke:
        signaux_fraude.append(f"🚨 FRAUDE: Nom différent détecté - Document actuel: '{nom_actuel}', Document précédent: '{nom_stocke}'")
    
    # Vérifier le prénom
    if prenom_actuel and prenom_stocke and prenom_actuel != prenom_stocke:
        signaux_fraude.append(f"🚨 FRAUDE: Prénom différent détecté - Document actuel: '{prenom_actuel}', Document précédent: '{prenom_stocke}'")
    
    # Vérifier le sexe
    if sexe_actuel_norm and sexe_stocke_norm and sexe_actuel_norm != sexe_stocke_norm:
        signaux_fraude.append(f"🚨 FRAUDE: Sexe différent détecté - Document actuel: '{sexe_actuel_norm}', Document précédent: '{sexe_stocke_norm}'")
    
    if signaux_fraude:
        message = "⚠️ INFORMATIONS À VÉRIFIER - FRAUDE SUSPECTÉE: Incohérence détectée entre les documents (nom, prénom ou sexe différent)"
        return False, signaux_fraude, message
    
    return True, [], "✅ Informations cohérentes entre les documents"

# --- Préparer données pour modèle ML (optionnel) ---
def preparer_donnees_modele(infos_sante):
    """Prépare les données pour un modèle ML si nécessaire"""
    def oui_non(val):
        if val == "Oui" or val is True:
            return 1
        return 0
    
    data = {
        "hypertension": oui_non(infos_sante["historique_medical"].get("Hypertension artérielle", False)),
        "diabete": oui_non(infos_sante["historique_medical"].get("Diabète", False)),
        "maladies_cardiaques": oui_non(infos_sante["historique_medical"].get("Maladies cardiaques", False)),
        "hospitalisation_recente": oui_non(infos_sante["historique_medical"].get("hospitalisation_recente") == "Oui"),
        "fumeur": oui_non(infos_sante["mode_vie"].get("fumeur") == "Oui"),
        "alcool": oui_non(infos_sante["mode_vie"].get("alcool") == "Oui"),
        "activite_physique": oui_non(infos_sante["mode_vie"].get("activite_physique") == "Oui"),
    }
    return [list(data.values())]

# --- Fonction principale d'analyse ---
def analyser_document(filepath, infos_client_reference=None):
    """
    Fonction principale qui analyse un document (PDF ou image) et retourne toutes les métriques
    
    Args:
        filepath: Chemin vers le fichier à analyser
        infos_client_reference: Informations personnelles du client de référence (pour comparaison)
    """
    if not os.path.exists(filepath):
        return {"message": "Fichier introuvable", "fichier": filepath, "status": "erreur"}
    
    try:
        # 1. Extraction OCR
        texte, type_fichier, confiance_ocr = extraire_texte_ocr(filepath)
        
        # 2. Détection du type de document
        type_document = detecter_type_document(texte, filepath)
        
        # 3. Extraction des dates du document
        dates_document = extraire_dates_document(texte)
        
        # 4. Vérification de l'expiration du document
        est_expire, jours_restants, message_expiration = verifier_expiration_document(
            dates_document.get("date_expiration")
        )
        
        # 5. Vérification de la qualité du document
        qualite_ok, message_qualite, besoin_nouveau_fichier = verifier_qualite_document(
            confiance_ocr, texte, filepath
        )
        
        # 6. Extraction des informations
        infos_personnelles = extraire_infos_personnelles(texte)
        infos_sante = extraire_infos_sante(texte)
        
        # 7. Vérification de la complétude des informations
        est_complet, champs_manquants, message_completude, doit_verifier = verifier_completude_informations(
            infos_personnelles, infos_sante, type_document
        )
        
        # 7b. Vérification de la cohérence entre documents (si plusieurs fichiers)
        est_coherent_docs, signaux_fraude_coherence, message_coherence = verifier_coherence_documents(
            infos_personnelles, infos_client_reference
        )
        
        # 8. Calcul des scores
        score_confiance = calculer_score_confiance(infos_personnelles, infos_sante, confiance_ocr)
        score_coherence, incohérences, signaux_fraude = calculer_score_coherence(infos_personnelles, infos_sante)
        score_risque, probabilite_acceptation, niveau_risque, facteurs_risque = calculer_risque_et_acceptation(infos_sante)
        
        # 9. Ajouter les signaux de fraude liés au document
        if est_expire:
            signaux_fraude.append(f"🚨 FRAUDE: Document expiré - {message_expiration}")
            probabilite_fraude_base = 0.8  # Fraude très probable si document expiré
        else:
            probabilite_fraude_base = 0.0
        
        if besoin_nouveau_fichier:
            signaux_fraude.append(f"⚠️ Document de mauvaise qualité - {message_qualite}")
        
        # Ajouter les signaux de fraude de cohérence entre documents
        if signaux_fraude_coherence:
            signaux_fraude.extend(signaux_fraude_coherence)
            incohérences.append(message_coherence)
        
        # Ajouter message de complétude seulement si doit_verifier est True
        if doit_verifier and not est_complet:
            signaux_fraude.append(f"⚠️ Informations incomplètes - {message_completude}")
            incohérences.append(message_completude)
        
        # 10. Calcul des probabilités de fraude et confiance assureur
        probabilite_fraude, niveau_fraude = calculer_probabilite_fraude(
            signaux_fraude, incohérences, score_coherence, confiance_ocr
        )
        
        # Si document expiré, forcer la probabilité de fraude à élevée
        if est_expire:
            probabilite_fraude = max(probabilite_fraude, 0.8)
            niveau_fraude = "TRÈS ÉLEVÉ"
        
        probabilite_confiance_assureur, niveau_confiance_assureur = calculer_probabilite_confiance_assureur(
            score_coherence, confiance_ocr, signaux_fraude, probabilite_fraude, probabilite_acceptation
        )
        
        # 11. Génération de l'avis et commentaire
        verification_doc = {
            "type_document": type_document,
            "dates_document": dates_document,
            "est_expire": est_expire,
            "jours_restants": jours_restants,
            "message_expiration": message_expiration,
            "qualite_ok": qualite_ok,
            "message_qualite": message_qualite,
            "besoin_nouveau_fichier": besoin_nouveau_fichier,
            "est_complet": est_complet,
            "champs_manquants": champs_manquants,
            "message_completude": message_completude
        }
        
        avis, commentaire = generer_avis_et_commentaire(
            score_risque, probabilite_acceptation, niveau_risque, facteurs_risque,
            score_coherence, incohérences, infos_sante, signaux_fraude, probabilite_fraude, probabilite_confiance_assureur,
            verification_document=verification_doc
        )
        
        # 12. Construction du résultat complet avec toutes les métriques
        resultat = {
            "fichier": os.path.basename(filepath),
            "type_fichier": type_fichier,
            "type_document": type_document,
            "texte_extrait": texte[:1000] + ("..." if len(texte) > 1000 else ""),
            "confiance_ocr": round(confiance_ocr * 100, 2) if confiance_ocr <= 1.0 else round(confiance_ocr, 2),  # En pourcentage si entre 0-1
            "infos_personnelles": infos_personnelles,
            "infos_sante": infos_sante,
            "verification_document": {
                "type_document": type_document,
                "dates_document": dates_document,
                "est_expire": est_expire,
                "jours_restants": jours_restants,
                "message_expiration": message_expiration,
                "qualite_ok": qualite_ok,
                "message_qualite": message_qualite,
                "besoin_nouveau_fichier": besoin_nouveau_fichier,
                "est_complet": est_complet,
                "doit_verifier": doit_verifier,
                "champs_manquants": champs_manquants,
                "message_completude": message_completude,
                "est_coherent_documents": est_coherent_docs,
                "message_coherence": message_coherence
            },
            "scores": {
                "score_confiance": score_confiance,
                "score_coherence": score_coherence,
                "score_risque": score_risque,
                "probabilite_acceptation": probabilite_acceptation,
                "probabilite_confiance_assureur": probabilite_confiance_assureur,
                "probabilite_fraude": probabilite_fraude
            },
            "evaluation": {
                "niveau_risque": niveau_risque,
                "niveau_fraude": niveau_fraude,
                "niveau_confiance_assureur": niveau_confiance_assureur,
                "avis": avis,
                "commentaire": commentaire,
                "facteurs_risque": facteurs_risque,
                "incoherences": incohérences,
                "signaux_fraude": signaux_fraude
            },
            "message": "Analyse effectuée avec succès ✅",
            "status": "ok"
        }
        
        # 13. Ajouter un message spécial si besoin d'un nouveau fichier
        if besoin_nouveau_fichier:
            resultat["message"] = "⚠️ Document de mauvaise qualité - Nouveau fichier requis"
            resultat["action_requise"] = "Veuillez fournir un nouveau fichier/document de meilleure qualité"
        
        # 14. Ajouter un message spécial si document expiré
        if est_expire:
            resultat["message"] = "🚨 FRAUDE: Document expiré"
            resultat["action_requise"] = "Document expiré - Vérification approfondie requise"
        
        return resultat
    
    except Exception as e:
        return {
            "message": f"Erreur lors de l'analyse: {str(e)}",
            "fichier": os.path.basename(filepath) if os.path.exists(filepath) else filepath,
            "status": "erreur",
            "erreur": str(e)
        }

# --- Exemple d'utilisation ---
if __name__ == "__main__":
    fichier_test = "test.pdf"  # Remplace par ton fichier
    if os.path.exists(fichier_test):
        resultat = analyser_document(fichier_test)
        import json
        print(json.dumps(resultat, indent=2, ensure_ascii=False))
    else:
        print(f"Fichier {fichier_test} non trouvé")
