# Connexion de l'app mobile au backend local (émulateur Android)

Quand l'app affiche **« Timeout »** ou **« No response »** vers `http://10.0.2.2:8000`, l'émulateur ne peut pas joindre le backend sur votre PC. Suivez ces étapes.

## 1. Démarrer le backend avec `--host 0.0.0.0`

Le backend doit écouter sur **toutes les interfaces** (pas seulement localhost), sinon l'émulateur (10.0.2.2) ne peut pas s'y connecter.

**À la racine du projet** (dossier `Mobility Health`, pas `mobile-app`) :

```powershell
# Option A : script (recommandé)
.\scripts\start_backend.ps1

# Option B : commande manuelle
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Vérifiez dans la console du backend qu'il affiche bien quelque chose comme :
`Uvicorn running on http://0.0.0.0:8000`

## 2. Vérifier que le port 8000 répond

Sur votre PC (PowerShell) :

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing | Select-Object -ExpandProperty Content
```

Si vous voyez `{"status":"healthy"}` (ou similaire), le backend répond. Sinon, il n'est pas démarré ou pas lancé depuis la bonne racine de projet.

## 3. Autoriser le port 8000 dans le pare-feu Windows

Sinon l'émulateur (qui est vu comme une autre « machine ») peut être bloqué.

- **Pare-feu Windows** → Paramètres avancés → Règles de trafic entrant → Nouvelle règle → Port → TCP 8000 → Autoriser la connexion.
- Ou en PowerShell **en administrateur** (à exécuter une seule fois) :

```powershell
New-NetFirewallRule -DisplayName "Mobility Health Backend 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

## 4. Fichier `.env` de l'app mobile

Le fichier `mobile-app/.env` doit contenir (pour l’émulateur Android) :

```env
API_BASE_URL=http://10.0.2.2:8000/api/v1
API_CONNEXION_BACKEND=http://10.0.2.2:8000
```

Pour un **appareil physique** sur le même Wi‑Fi, remplacez `10.0.2.2` par l’IP de votre PC (ex. `192.168.1.100`).

## 5. Relancer l'app Flutter

Après toute modification du `.env`, faire un **redémarrage complet** de l’app (arrêt puis `flutter run`), car le `.env` est lu au démarrage.

---

**Récap** : Backend lancé avec `--host 0.0.0.0`, port 8000 ouvert dans le pare-feu, `.env` avec `10.0.2.2:8000`, puis relancer l’app.
