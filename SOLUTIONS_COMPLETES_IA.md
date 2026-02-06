# 🛠️ Solutions Complètes - Intégration Module IA

**Session du** : 5 Décembre 2025  
**Projet** : Mobility Health - Module IA de Souscription

---

## 📋 Table des Matières

1. [Problème : Module IA non connecté au Backend](#1-problème--module-ia-non-connecté-au-backend)
2. [Problème : Base de données non initialisée](#2-problème--base-de-données-non-initialisée)
3. [Problème : Utilisateur admin inexistant](#3-problème--utilisateur-admin-inexistant)
4. [Problème : Extraction questionnaire médical incorrecte](#4-problème--extraction-questionnaire-médical-incorrecte)
5. [Problème : Erreur "Informations de voyage manquantes"](#5-problème--erreur-informations-de-voyage-manquantes)
6. [Problème : Pays capture trop de texte](#6-problème--pays-capture-trop-de-texte)
7. [Problème : Frontend pointe vers production](#7-problème--frontend-pointe-vers-production)
8. [Problème : Frontend force HTTPS](#8-problème--frontend-force-https)
9. [Configuration complète du module IA](#9-configuration-complète-du-module-ia)

---

## 1. Problème : Module IA non connecté au Backend

### Symptôme
Le module IA existait dans `projet_ia_souscription` mais n'était pas intégré au backend FastAPI `Mobility-Health`.

### Solution
Copier le module IA dans le backend et créer un endpoint API.

#### Étape 1 : Copier le dossier ia_module
```powershell
Copy-Item -Path "C:\Users\MARIANA K\Downloads\projet_ia_souscription\projet_ia_souscription\ia_module" -Destination "C:\Users\MARIANA K\Downloads\Mobility-Health\app\ia_module" -Recurse
```

#### Étape 2 : Créer le fichier endpoint `app/api/v1/ia.py`
```python
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

from app.api.v1.auth import get_current_user
from app.models.user import User

# Import du module IA
from app.ia_module import analyser_document, formater_pour_agent_production

router = APIRouter(prefix="/ia", tags=["IA - Analyse Documents"])


class AnalyseResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None


@router.post("/analyser-documents", response_model=AnalyseResponse)
async def analyser_documents(
    fichiers: List[UploadFile] = File(...),
    demande_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
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
            demande_id=demande_id
        )
        
        return AnalyseResponse(
            success=True,
            message=f"{len(fichiers)} document(s) analysé(s) avec succès",
            data=resultat_final
        )
        
    finally:
        for fichier_info in fichiers_temp:
            try:
                os.unlink(fichier_info["path"])
            except:
                pass


@router.get("/health")
async def health_check():
    try:
        from app.ia_module import analyser_document
        return {
            "status": "ok",
            "module": "ia_module",
            "message": "Module IA opérationnel"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

#### Étape 3 : Enregistrer le router dans `app/api/v1/__init__.py`
```python
from app.api.v1 import ia

# Dans la liste des routers :
api_router.include_router(ia.router)
```

---

## 2. Problème : Base de données non initialisée

### Symptôme
```
sqlalchemy.exc.OperationalError: no such table: users
```

### Solution
Créer les tables avec SQLAlchemy directement.

```powershell
cd "C:\Users\MARIANA K\Downloads\Mobility-Health"
python -c "from app.core.database import engine, Base; from app.models import *; Base.metadata.create_all(bind=engine); print('Tables creees!')"
```

---

## 3. Problème : Utilisateur admin inexistant

### Symptôme
Impossible de se connecter car aucun utilisateur n'existe.

### Solution
Créer l'utilisateur admin avec bcrypt.

```powershell
cd "C:\Users\MARIANA K\Downloads\Mobility-Health"
python -c "
import bcrypt
from app.core.database import SessionLocal
from app.models.user import User

db = SessionLocal()

existing = db.query(User).filter(User.email == 'admin@mobilityhealth.com').first()
if existing:
    print('Admin existe deja!')
else:
    hashed = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    admin = User(
        email='admin@mobilityhealth.com',
        username='admin',
        hashed_password=hashed,
        full_name='Administrateur',
        role='admin',
        is_active=True,
        is_superuser=True
    )
    db.add(admin)
    db.commit()
    print('Admin cree!')

db.close()
"
```

### Identifiants
- **Email** : `admin@mobilityhealth.com`
- **Mot de passe** : `admin123`

---

## 4. Problème : Extraction questionnaire médical incorrecte

### Symptôme
Le module détectait "Hypertension: true", "Diabète: true" alors que le PDF disait "Non" pour tout.

### Cause
Le code cherchait juste si le mot "Hypertension" existait dans le texte, pas s'il était suivi de "Oui" ou "Non".

### Solution
Modifier `app/ia_module/analyse.py` (lignes 192-222) :

#### AVANT :
```python
maladies = [
    "Hypertension artérielle",
    "Diabète",
    # ...
]

for maladie in maladies:
    pattern = re.escape(maladie)
    data["historique_medical"][maladie] = bool(re.search(pattern, texte, re.IGNORECASE))
```

#### APRÈS :
```python
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
```

---

## 5. Problème : Erreur "Informations de voyage manquantes"

### Symptôme
```json
{
  "incoherences": ["⚠️ DOCUMENT À VÉRIFIER: Informations de voyage manquantes."]
}
```

### Cause
Le module vérifiait les informations de voyage qui ne sont plus requises.

### Solution
Modifier `app/ia_module/analyse.py` (fonction `verifier_completude_informations`) :

#### AVANT :
```python
# Vérifier les informations de voyage
infos_voyage_remplis = 0
if infos_personnelles.get("frequence_voyage_mois"):
    infos_voyage_remplis += 1
# ... (beaucoup de code)

a_infos_voyage = infos_voyage_remplis >= 1

if a_questionnaire_medical and a_infos_personnelles and a_infos_voyage:
    return True, [], "✅ Informations complètes", False
```

#### APRÈS :
```python
# Logique simplifiée : vérifier questionnaire médical + infos personnelles
# (Les informations de voyage ne sont plus requises)
a_questionnaire_medical = champs_sante_remplis >= 2
a_infos_personnelles = champs_perso_remplis >= 2

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
```

---

## 6. Problème : Pays capture trop de texte

### Symptôme
```json
{
  "pays": "Congolaise Profession"
}
```
Au lieu de juste "Congolaise".

### Cause
Le regex capturait les espaces et continuait jusqu'au prochain mot.

### Solution
Modifier `app/ia_module/analyse.py` :

#### AVANT :
```python
"pays": [
    r"Pays\s*:\s*([A-Za-z][a-zA-Z\s\-']+?)(?:\s+Mari|\s+Nbre|\s+[0-9])",
    r"Nationalit[eé]\s*:\s*([A-Za-z][a-zA-Z\s\-']+)"
]
```

#### APRÈS :
```python
"pays": [
    r"Pays\s*:\s*([A-Za-z][a-zA-Zéèêëàâäùûüôöîïç\-]+)",
    r"Nationalit[eé]\s*:\s*([A-Za-z][a-zA-Zéèêëàâäùûüôöîïç\-]+)"
]
```

**Note** : Suppression de `\s` (espaces) dans la classe de caractères pour arrêter la capture au premier espace.

---

## 7. Problème : Frontend pointe vers production

### Symptôme
```
Erreur: Impossible de se connecter au serveur.
Vérifiez que l'API est accessible sur https://mobility-health.ittechmed.com
```

### Cause
L'URL API était configurée pour la production.

### Solution
Modifier `frontend-simple/js/api.js` (ligne 2) :

#### AVANT :
```javascript
const API_BASE_URL = 'https://mobility-health.ittechmed.com/api/v1';
```

#### APRÈS :
```javascript
// Production: https://mobility-health.ittechmed.com/api/v1
// Local: http://127.0.0.1:8000/api/v1
const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';
```

---

## 8. Problème : Frontend force HTTPS

### Symptôme
```
ERR_SSL_PROTOCOL_ERROR
URL: https://127.0.0.1:8000/api/v1/...
```

### Cause
Le code JavaScript forçait la conversion HTTP → HTTPS.

### Solution
Supprimer les lignes qui forcent HTTPS dans `frontend-simple/js/api.js` :

#### Lignes à supprimer/commenter :

**Ligne ~168-171 :**
```javascript
// SUPPRIMER :
if (url.startsWith('http://')) {
    url = url.replace('http://', 'https://');
}
```

**Ligne ~206-209 :**
```javascript
// SUPPRIMER :
if (url.startsWith('http://')) {
    console.error('❌ ERREUR: URL HTTP détectée, conversion en HTTPS:', url);
    url = url.replace('http://', 'https://');
}
```

**Ligne ~227-229 :**
```javascript
// SUPPRIMER :
if (!url.startsWith('https://')) {
    throw new Error(`URL non sécurisée détectée: ${url}. Toutes les requêtes doivent utiliser HTTPS.`);
}
```

---

## 9. Configuration complète du module IA

### Fichier `app/ia_module/config.py`

```python
"""
Configuration du module IA - Détection automatique Windows/Linux
"""
import os
import platform

class IAConfig:
    def __init__(self):
        self.is_windows = platform.system() == "Windows"
        self.is_linux = platform.system() == "Linux"
        
        if self.is_windows:
            # Configuration Windows
            self.TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            
            # Chercher Poppler dans différents emplacements
            poppler_paths = [
                r"C:\Program Files\poppler-25.07.0\Library\bin",
                r"C:\Program Files\poppler-24.08.0\Library\bin",
                r"C:\Program Files\poppler\Library\bin",
            ]
            self.POPPLER_PATH = None
            for path in poppler_paths:
                if os.path.exists(path):
                    self.POPPLER_PATH = path
                    break
            
            if not self.POPPLER_PATH:
                self.POPPLER_PATH = r"C:\Program Files\poppler-25.07.0\Library\bin"
        else:
            # Configuration Linux (production)
            self.TESSERACT_CMD = "/usr/bin/tesseract"
            self.POPPLER_PATH = "/usr/bin"
        
        # Configuration API (si utilisé en microservice)
        self.API_HOST = os.getenv("IA_API_HOST", "127.0.0.1")
        self.API_PORT = int(os.getenv("IA_API_PORT", "8001"))
    
    def print_config(self):
        print(f"=== Configuration Module IA ===")
        print(f"Système: {'Windows' if self.is_windows else 'Linux'}")
        print(f"Tesseract: {self.TESSERACT_CMD}")
        print(f"Poppler: {self.POPPLER_PATH}")
        print(f"Tesseract existe: {os.path.exists(self.TESSERACT_CMD)}")
        print(f"Poppler existe: {os.path.exists(self.POPPLER_PATH) if self.POPPLER_PATH else False}")

config = IAConfig()
```

### Fichier `.env` (pour développement local)

```env
# Database
DATABASE_URL=sqlite:///./mobility_health.db

# Redis (optionnel en local)
REDIS_URL=redis://localhost:6379/0

# Minio (optionnel en local)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# JWT
SECRET_KEY=dev-secret-key-pour-test-local-mobility-health-2024
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application
DEBUG=True
ENVIRONMENT=development
```

### Dépendances à installer

```powershell
pip install pytesseract Pillow pdf2image numpy scikit-learn filetype
```

### Outils externes requis

| Outil | Téléchargement |
|-------|----------------|
| Tesseract OCR | https://github.com/UB-Mannheim/tesseract/wiki |
| Poppler | https://github.com/oschwartz10612/poppler-windows/releases |

---

## 📋 Commandes utiles

### Démarrer le backend
```powershell
cd "C:\Users\MARIANA K\Downloads\Mobility-Health"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Démarrer le frontend
```powershell
cd "C:\Users\MARIANA K\Downloads\Mobility-Health\frontend-simple"
python server.py
```

### Tester le module IA
```powershell
cd "C:\Users\MARIANA K\Downloads\Mobility-Health"
python -c "from app.ia_module import analyser_document; print('OK')"
```

### Créer un utilisateur
```powershell
python scripts/create_test_users.py
```

---

## ✅ Résultat Final

Après toutes ces corrections, le système fonctionne :

1. ✅ Backend FastAPI sur http://127.0.0.1:8000
2. ✅ Frontend Web sur http://localhost:3000
3. ✅ Module IA intégré et fonctionnel
4. ✅ Extraction correcte des informations du PDF
5. ✅ Questionnaire médical correctement analysé
6. ✅ Connexion frontend ↔ backend OK

---

**Fin du document de solutions**

