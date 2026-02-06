# 📋 Documentation Intégration Module IA - Mobility Health

**Date de création** : 5 Décembre 2025  
**Auteur** : Équipe IA  
**Version** : 1.0

---

## 📌 Résumé

Ce document décrit l'intégration complète du **Module IA d'analyse de documents** dans le backend FastAPI de Mobility Health. Le module permet d'analyser automatiquement les documents de souscription (questionnaires médicaux, pièces d'identité, etc.) et de fournir une recommandation à l'Agent de Production.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MOBILITY HEALTH                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📱 Mobile Flutter     🌐 Frontend Web                      │
│         │                    │                              │
│         └────────┬───────────┘                              │
│                  │                                          │
│                  ▼                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              BACKEND FASTAPI                         │   │
│  │  ┌─────────────────────────────────────────────┐    │   │
│  │  │  app/                                        │    │   │
│  │  │  ├── api/v1/                                │    │   │
│  │  │  │   ├── auth.py                            │    │   │
│  │  │  │   ├── subscriptions.py                   │    │   │
│  │  │  │   └── ia.py  ← NOUVEAU ENDPOINT IA       │    │   │
│  │  │  │                                          │    │   │
│  │  │  ├── ia_module/  ← MODULE IA INTÉGRÉ        │    │   │
│  │  │  │   ├── __init__.py                        │    │   │
│  │  │  │   ├── analyse.py                         │    │   │
│  │  │  │   ├── formateur.py                       │    │   │
│  │  │  │   └── config.py                          │    │   │
│  │  │  │                                          │    │   │
│  │  │  └── core/, models/, services/...           │    │   │
│  │  └─────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Fichiers Ajoutés/Modifiés

### 1. Module IA (`app/ia_module/`)

| Fichier | Description |
|---------|-------------|
| `__init__.py` | Exports des fonctions principales |
| `analyse.py` | OCR, extraction d'informations, calcul des scores |
| `formateur.py` | Formatage des résultats par rôle (Médecin, Agent Technique, Agent Production) |
| `config.py` | Configuration auto Windows/Linux (Tesseract, Poppler) |

### 2. Endpoint API (`app/api/v1/ia.py`)

Nouveau fichier créé pour exposer les fonctionnalités IA via l'API REST.

### 3. Fichiers Modifiés

| Fichier | Modification |
|---------|--------------|
| `app/api/v1/__init__.py` | Ajout de l'import du router IA |
| `requirements.txt` | Ajout des dépendances IA |
| `.env` | Créé pour configuration locale |

---

## 🔌 Endpoints API IA

### `GET /api/v1/ia/health`
Vérifie que le module IA est opérationnel.

**Réponse :**
```json
{
  "status": "ok",
  "module": "ia_module",
  "message": "Module IA opérationnel"
}
```

### `POST /api/v1/ia/analyser-documents`
Analyse des documents pour l'Agent de Production.

**Paramètres :**
- `fichiers` (required) : Liste de fichiers PDF/images
- `demande_id` (optional) : ID de la demande de souscription

**Headers :**
- `Authorization: Bearer <token>`

**Exemple de réponse :**
```json
{
  "success": true,
  "message": "1 document(s) analysé(s) avec succès",
  "data": {
    "vue": "agent_production",
    "demande_id": "DEM-20251205-120413",
    "resume_executif": {
      "decision_ia": "✅ ACCEPTATION RECOMMANDÉE",
      "score_global_acceptation": "85.0/100",
      "pret_pour_approbation": true
    },
    "client": {
      "informations_personnelles": {
        "nom": "OBAMA",
        "prenom": "Ten",
        "date_naissance": "01/12/1994",
        "sexe": "M",
        "pays": "Congolaise"
      }
    },
    "evaluation_medicale": {
      "questionnaire_medical": {
        "historique_medical": {
          "Hypertension artérielle": false,
          "Diabète": false,
          "Maladies cardiaques": false
        }
      },
      "risque_medical": "Faible"
    },
    "scores_ia_detailles": {
      "probabilite_acceptation": "85%",
      "probabilite_fraude": "5%",
      "score_coherence": "90/100"
    }
  }
}
```

### `POST /api/v1/ia/analyser-avec-statut-medical`
Analyse avec statut médical pré-rempli (après validation du Médecin MH).

---

## 🔧 Configuration

### Fichier `app/ia_module/config.py`

```python
class IAConfig:
    def __init__(self):
        self.is_windows = platform.system() == "Windows"
        
        if self.is_windows:
            self.TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            self.POPPLER_PATH = r"C:\Program Files\poppler-25.07.0\Library\bin"
        else:
            # Linux (production)
            self.TESSERACT_CMD = "/usr/bin/tesseract"
            self.POPPLER_PATH = "/usr/bin"
```

### Dépendances Requises

```txt
# Dans requirements.txt
pytesseract>=0.3.10
Pillow>=10.0.0
pdf2image>=1.16.0
numpy>=1.24.0
scikit-learn>=1.3.0
filetype>=1.2.0
```

### Outils Externes

| Outil | Windows | Linux |
|-------|---------|-------|
| Tesseract OCR | `C:\Program Files\Tesseract-OCR\` | `apt install tesseract-ocr` |
| Poppler | `C:\Program Files\poppler-25.07.0\` | `apt install poppler-utils` |

---

## 🔄 Workflow d'Intégration

### Étape 1 : Utilisateur soumet une demande

```
Mobile/Web → Backend → Stocke fichiers (MinIO/disque)
```

### Étape 2 : Backend appelle le Module IA

```python
# Dans le service de souscription
from app.ia_module import analyser_document, formater_pour_agent_production

def traiter_demande(demande_id, fichiers):
    # Analyser chaque document
    resultats = []
    for fichier in fichiers:
        resultat = analyser_document(fichier.path)
        resultats.append({
            "status": resultat.get("status", "ok"),
            "nom_fichier": fichier.filename,
            "analyse": resultat
        })
    
    # Formater pour l'Agent de Production
    resultat_final = formater_pour_agent_production(
        resultats_analyse=resultats,
        demande_id=demande_id
    )
    
    # Stocker le résultat IA
    sauvegarder_resultat_ia(demande_id, resultat_final)
    
    return resultat_final
```

### Étape 3 : Agent de Production voit le résultat

L'Agent de Production accède au dashboard et voit :
- Recommandation IA (Accepter/Rejeter/Vérifier)
- Score de confiance
- Détails de l'analyse
- Signaux de fraude éventuels

---

## 📊 Ce que le Module IA Analyse

### 1. Informations Personnelles
- Nom, Prénom
- Date de naissance, Âge
- Sexe
- Nationalité/Pays
- Téléphone, Email
- Adresse

### 2. Questionnaire Médical
- Historique médical (Hypertension, Diabète, Maladies cardiaques, etc.)
- Santé actuelle
- Mode de vie (Fumeur, Alcool, Activité physique)
- Allergies
- Santé mentale

### 3. Documents
- Type de document (Passeport, CNI, Questionnaire)
- Qualité OCR
- Dates (émission, expiration)
- Cohérence des informations

### 4. Scores Calculés
- **Probabilité d'acceptation** : 0-100%
- **Probabilité de fraude** : 0-100%
- **Score de cohérence** : 0-100
- **Score de confiance assureur** : 0-100%

---

## 🛡️ Rôles et Accès

| Rôle | Accès |
|------|-------|
| **Médecin MH** | Questionnaire médical complet + Validation médicale |
| **Agent Technique** | Documents + Vérification fraude/incohérences |
| **Agent Production** | Vue complète + Décision finale |
| **Assureur** | Vue limitée (pas de détails médicaux) |

---

## 🐛 Corrections Apportées

### 1. Extraction Questionnaire Médical
**Problème** : Détectait "Hypertension: true" alors que le PDF disait "Non"  
**Solution** : Regex améliorées pour détecter "Maladie : Oui/Non"

```python
# Avant
data["historique_medical"][maladie] = bool(re.search(pattern, texte))

# Après
pattern_oui = rf"{maladie_pattern}\s*:\s*(Oui|OUI|oui|Qui)"  # "Qui" car OCR lit parfois mal
pattern_non = rf"{maladie_pattern}\s*:\s*(Non|NON|non)"
```

### 2. Informations de Voyage
**Problème** : Erreur "Informations de voyage manquantes"  
**Solution** : Suppression de la vérification des infos de voyage (non requises)

### 3. Extraction Pays
**Problème** : Capturait "Congolaise Profession" au lieu de "Congolaise"  
**Solution** : Regex limitée aux caractères alphabétiques sans espaces

```python
# Avant
r"Nationalit[eé]\s*:\s*([A-Za-z][a-zA-Z\s\-']+)"

# Après
r"Nationalit[eé]\s*:\s*([A-Za-z][a-zA-Zéèêëàâäùûüôöîïç\-]+)"
```

---

## 🧪 Tests

### Test via Swagger

1. Ouvrir http://127.0.0.1:8000/docs
2. Cliquer sur "Authorize"
3. Entrer : `admin@mobilityhealth.com` / `admin123`
4. Tester `POST /api/v1/ia/analyser-documents`
5. Uploader un PDF

### Test en ligne de commande

```powershell
cd C:\Users\MARIANA K\Downloads\Mobility-Health

python -c "
from app.ia_module.analyse import analyser_document
resultat = analyser_document('chemin/vers/document.pdf')
print(resultat)
"
```

---

## 📦 Déploiement Production

### Dockerfile (à ajouter)

```dockerfile
FROM python:3.10-slim

# Installer Tesseract et Poppler
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-fra \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copier le code
COPY . /app
WORKDIR /app

# Installer les dépendances Python
RUN pip install -r requirements.txt

# Lancer l'application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 📝 Notes Importantes

1. **L'IA est un outil d'aide à la décision** - La décision finale reste humaine (Agent de Production)

2. **Les validations médecin/technique sont externes** - Le backend doit passer ces statuts à l'IA

3. **OCR peut faire des erreurs** - Prévoir une révision humaine pour les cas limites

4. **Configuration auto** - Le module détecte Windows/Linux automatiquement

---

## 📞 Support

Pour toute question sur l'intégration du module IA :
- Consulter ce document
- Tester via Swagger (`/docs`)
- Vérifier les logs du backend

---

**Fin du document**

