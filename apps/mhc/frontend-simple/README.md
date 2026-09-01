# Mobility Health Frontend - Version HTML/JS (v2.0)

Version frontend simple utilisant uniquement HTML, CSS et JavaScript (sans Node.js ni dépendances).

## 🌿 Branches

- **Frontend-HTML**: Version actuelle avec HTML/JS (v2.0)
- **main/master**: Peut contenir l'ancienne version React (v1.0)

## Structure

```
frontend-simple/
├── index.html                 # Page d'accueil
├── questionnaire-short.html   # Formulaire questionnaire court
├── questionnaire-long.html    # Formulaire questionnaire long
├── attestations.html          # Liste des attestations
├── attestation-view.html      # Visualisation d'une attestation PDF
├── css/
│   └── style.css             # Styles CSS
└── js/
    ├── api.js                # Fonctions API
    ├── auth.js               # Gestion authentification
    ├── questionnaire-short.js
    ├── questionnaire-long.js
    ├── attestations.js
    └── attestation-view.js
```

## Utilisation

### 1. Ouvrir les fichiers HTML

Ouvrez simplement les fichiers HTML dans votre navigateur :

- **Double-cliquez** sur `index.html` pour ouvrir la page d'accueil
- Ou utilisez un serveur web local (recommandé pour éviter les problèmes CORS)

### 2. Utiliser un serveur web local (recommandé)

#### Option A : Python (si installé)

```bash
cd frontend-simple
python -m http.server 3000
```

Puis ouvrez : http://localhost:3000

#### Option B : PHP (si installé)

```bash
cd frontend-simple
php -S localhost:3000
```

#### Option C : Extension VS Code

Installez l'extension "Live Server" dans VS Code, puis :
- Clic droit sur `index.html`
- Sélectionnez "Open with Live Server"

### 3. Configuration de l'API

Par défaut, l'API est configurée pour `http://localhost:8000/api/v1`.

Pour changer l'URL de l'API, modifiez la constante dans `js/api.js` :

```javascript
const API_BASE_URL = 'http://votre-serveur:8000/api/v1';
```

### 4. Authentification

Le token d'authentification est stocké dans `localStorage` avec la clé `access_token`.

Pour vous connecter, vous devez :
1. Appeler l'endpoint de login de votre API
2. Stocker le token dans `localStorage` :

```javascript
localStorage.setItem('access_token', 'votre-token-ici');
```

## Pages disponibles

### Pages publiques
1. **index.html** - Page d'accueil avec navigation
2. **questionnaire-short.html** - Formulaire questionnaire court
3. **questionnaire-long.html** - Formulaire questionnaire long
4. **attestations.html** - Liste des attestations par souscription
5. **attestation-view.html** - Visualisation PDF d'une attestation

### Back Office (nécessite authentification)

#### Pages de connexion
1. **login.html** - Page de connexion au back office (tous les rôles)

#### Dashboards par rôle
2. **admin-dashboard.html** - Tableau de bord administrateur (rôle: `admin`)
3. **doctor-dashboard.html** - Tableau de bord médecin (rôle: `doctor`)
4. **hospital-dashboard.html** - Tableau de bord administrateur hôpital (rôle: `hospital_admin`)
5. **finance-dashboard.html** - Tableau de bord gestionnaire finance (rôle: `finance_manager`)
6. **sos-dashboard.html** - Tableau de bord opérateur SOS (rôle: `sos_operator`)

#### Pages de gestion (par rôle)
7. **admin-products.html** - Gestion des produits d'assurance (rôle: `admin`)
8. **admin-subscriptions.html** - Gestion des souscriptions (rôles: `admin`, `finance_manager`)
9. **admin-users.html** - Gestion des utilisateurs (rôle: `admin`)
10. **admin-attestations.html** - Validation des attestations (rôles: `admin`, `doctor`, `hospital_admin`)

## Fonctionnalités

- ✅ Formulaires de questionnaires (court et long)
- ✅ Visualisation des attestations PDF
- ✅ Appels API avec gestion d'erreurs
- ✅ Interface responsive
- ✅ Messages d'alerte
- ✅ Validation des formulaires
- ✅ Système de routage basé sur les rôles
- ✅ Vérification des permissions par page

## Accès au Back Office

1. **Ouvrir la page de connexion** : http://localhost:3000/login.html

2. **Se connecter** avec un compte :
   - Nom d'utilisateur : votre username
   - Mot de passe : votre mot de passe

3. **Rôles disponibles et leurs permissions** :
   - **`admin`** : Accès complet au back office
     - Dashboard : `admin-dashboard.html`
     - Peut gérer : produits, souscriptions, utilisateurs, attestations
   
   - **`doctor`** : Validation médicale des attestations
     - Dashboard : `doctor-dashboard.html`
     - Peut valider : attestations (validation médicale)
   
   - **`hospital_admin`** : Validation technique des attestations
     - Dashboard : `hospital-dashboard.html`
     - Peut valider : attestations (validation technique)
   
   - **`finance_manager`** : Gestion des souscriptions et finances
     - Dashboard : `finance-dashboard.html`
     - Peut gérer : souscriptions, finances
   
   - **`sos_operator`** : Gestion des alertes SOS
     - Dashboard : `sos-dashboard.html`
     - Peut gérer : alertes SOS
   
   - **`user`** : Utilisateur standard
     - Redirigé vers : `index.html` (page d'accueil publique)
     - Peut utiliser : questionnaires, attestations (lecture seule)

4. **Après connexion**, vous serez automatiquement redirigé vers le dashboard approprié selon votre rôle.

## Notes

- Assurez-vous que le backend est lancé sur `http://localhost:8000`
- Les requêtes API nécessitent un token d'authentification (stocké dans localStorage)
- Pour éviter les problèmes CORS, utilisez un serveur web local plutôt que d'ouvrir directement les fichiers HTML
- Le token d'authentification est stocké dans `localStorage` et expire après 30 minutes (configurable)

