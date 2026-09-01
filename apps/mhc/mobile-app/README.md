# Mobility Health Mobile Application

Application mobile Flutter pour les utilisateurs de Mobility Health. Cette application consomme les APIs de l'application web.

## 📋 Prérequis

- Flutter SDK >= 3.0.0
- Dart SDK >= 3.0.0
- Android Studio / Xcode (pour le développement mobile)
- Backend Mobility Health en cours d'exécution

## 🚀 Installation

### 1. Installer Flutter

Suivez les instructions officielles : [https://flutter.dev/docs/get-started/install](https://flutter.dev/docs/get-started/install)

### 2. Cloner et configurer le projet

```bash
cd mobile-app
flutter pub get
```

### 3. Configuration de l'environnement

Copiez le fichier `.env.example` vers `.env` et configurez les variables :

```bash
cp .env.example .env
```

Éditez `.env` avec vos paramètres.

**Backend de production (Hostinger)** :

```env
API_BASE_URL=https://srv1324425.hstgr.cloud/api/v1
API_CONNEXION_BACKEND=https://srv1324425.hstgr.cloud
API_TIMEOUT=30000
ENVIRONMENT=production
APP_NAME=Mobility Health
APP_VERSION=1.0.0
```

**Développement local** : utilisez `http://localhost:8000/api/v1` ou l’IP de votre machine (ex: `http://192.168.1.100:8000/api/v1`).

### 4. Générer les assets

Créez les dossiers nécessaires :

```bash
mkdir -p assets/images
mkdir -p assets/icons
```

## 🏗️ Architecture

```
lib/
├── core/
│   ├── config/          # Configuration de l'application
│   ├── constants/       # Constantes
│   ├── network/         # Client API et intercepteurs
│   ├── routing/         # Navigation et routes
│   └── utils/           # Utilitaires (storage, etc.)
├── models/              # Modèles de données
├── providers/           # State management (Riverpod)
├── screens/             # Écrans de l'application
│   ├── auth/           # Authentification
│   ├── home/           # Accueil
│   └── splash/         # Écran de démarrage
└── services/            # Services API
    ├── auth_service.dart
    └── api_service.dart
```

## 🔧 Développement

### Lancer l'application

```bash
flutter run
```

### Mode debug

```bash
flutter run --debug
```

### Mode release

```bash
flutter run --release
```

### Build APK (Android)

```bash
flutter build apk --release
```

### Build iOS

```bash
flutter build ios --release
```

## 📱 Fonctionnalités

### ✅ Implémentées

- Authentification (Login/Register)
- Gestion des tokens (Access/Refresh)
- Stockage sécurisé des données
- Navigation avec GoRouter
- State management avec Riverpod
- Client API avec intercepteurs
- Gestion des erreurs

### 🚧 À implémenter

- Liste des produits d'assurance
- Gestion des souscriptions
- Questionnaires médicaux
- Attestations
- Alertes SOS
- Notifications push
- Paiements
- Documents
- Hôpitaux à proximité
- Dashboard utilisateur

## 🔐 Authentification

L'application utilise OAuth2 avec Bearer tokens :

- **Access Token** : Valide 30 minutes
- **Refresh Token** : Valide 7 jours

Les tokens sont stockés de manière sécurisée avec `flutter_secure_storage`.

## 🌐 API Endpoints

L'application consomme les endpoints suivants :

- `/api/v1/auth/*` - Authentification
- `/api/v1/products/*` - Produits d'assurance
- `/api/v1/subscriptions/*` - Souscriptions
- `/api/v1/voyages/*` - Projets de voyage
- `/api/v1/questionnaires/*` - Questionnaires
- `/api/v1/attestations/*` - Attestations
- `/api/v1/sos/*` - Alertes SOS
- `/api/v1/hospitals/*` - Hôpitaux
- `/api/v1/payments/*` - Paiements
- `/api/v1/notifications/*` - Notifications
- `/api/v1/documents/*` - Documents
- `/api/v1/dashboard/*` - Tableau de bord

## 🧪 Tests

```bash
# Tests unitaires
flutter test

# Tests d'intégration
flutter test integration_test
```

## 📦 Dépendances principales

- **riverpod** : State management
- **dio** : Client HTTP
- **go_router** : Navigation
- **flutter_secure_storage** : Stockage sécurisé
- **shared_preferences** : Stockage local
- **jwt_decoder** : Décodage des tokens JWT

## 🔄 Synchronisation avec le backend

L'application est configurée pour consommer les routes de l'API web. Assurez-vous que :

1. Le backend est en cours d'exécution
2. CORS est configuré pour autoriser les requêtes depuis l'application mobile
3. L'URL de l'API dans `.env` correspond à votre configuration backend

## 🐛 Dépannage

### Erreur de connexion API

- Vérifiez que le backend est démarré
- Vérifiez l'URL dans `.env`
- Pour Android, utilisez `10.0.2.2` au lieu de `localhost` dans l'émulateur
- Pour iOS, utilisez `localhost` ou l'IP de votre machine

### Erreur de build

```bash
flutter clean
flutter pub get
flutter run
```

## 📝 Notes de développement

- Les tokens sont automatiquement rafraîchis lorsqu'ils expirent
- Les erreurs 401 redirigent automatiquement vers la page de connexion
- Le state management utilise Riverpod pour une gestion réactive de l'état
- Les requêtes API incluent automatiquement le token d'authentification

## 📄 Licence

Propriétaire - Mobility Health

