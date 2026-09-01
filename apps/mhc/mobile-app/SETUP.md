# Guide de Configuration - Mobility Health Mobile

Ce guide vous aidera à configurer et lancer l'application mobile Flutter.

## 📋 Prérequis

1. **Flutter SDK** (version >= 3.0.0)
   - Télécharger depuis : https://flutter.dev/docs/get-started/install
   - Vérifier l'installation : `flutter doctor`

2. **Android Studio** ou **Xcode** (pour iOS)
   - Android Studio : https://developer.android.com/studio
   - Xcode : Disponible sur Mac App Store (macOS uniquement)

3. **Backend Mobility Health**
   - Le backend doit être en cours d'exécution
   - URL par défaut : `http://localhost:8000`

## 🚀 Installation Rapide

### Étape 1 : Installer les dépendances

```bash
cd mobile-app
flutter pub get
```

### Étape 2 : Configurer l'environnement

Créez un fichier `.env` à la racine du dossier `mobile-app` :

```bash
# Windows PowerShell
Copy-Item .env.example .env

# Linux/Mac
cp .env.example .env
```

Éditez le fichier `.env` :

```env
API_BASE_URL=http://localhost:8000/api/v1
API_TIMEOUT=30000
ENVIRONMENT=development
APP_NAME=Mobility Health
APP_VERSION=1.0.0
```

### Étape 3 : Configuration pour les appareils

#### Pour Android Emulator
Utilisez `10.0.2.2` au lieu de `localhost` :
```env
API_BASE_URL=http://10.0.2.2:8000/api/v1
```

#### Pour iOS Simulator
Utilisez `localhost` :
```env
API_BASE_URL=http://localhost:8000/api/v1
```

#### Pour appareil physique
Utilisez l'adresse IP de votre machine :
```env
API_BASE_URL=http://192.168.1.XXX:8000/api/v1
```

Pour trouver votre adresse IP :
- Windows : `ipconfig` (cherchez IPv4)
- Mac/Linux : `ifconfig` ou `ip addr`

### Étape 4 : Vérifier les appareils disponibles

```bash
flutter devices
```

### Étape 5 : Lancer l'application

```bash
flutter run
```

## 🔧 Configuration CORS du Backend

Assurez-vous que le backend autorise les requêtes depuis l'application mobile.

Dans `app/core/config.py`, ajoutez l'origine mobile aux `CORS_ORIGINS` :

```python
CORS_ORIGINS: List[str] = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    # Ajoutez l'origine mobile si nécessaire
]
```

Pour les applications mobiles, les requêtes peuvent ne pas nécessiter de configuration CORS spécifique, mais assurez-vous que `allow_credentials=True` est configuré.

## 📱 Build pour Production

### Android APK

```bash
flutter build apk --release
```

Le fichier APK sera dans : `build/app/outputs/flutter-apk/app-release.apk`

### Android App Bundle (pour Google Play)

```bash
flutter build appbundle --release
```

### iOS

```bash
flutter build ios --release
```

**Note** : Pour iOS, vous devez avoir un compte développeur Apple et configurer les certificats dans Xcode.

## 🧪 Tests

### Tests unitaires

```bash
flutter test
```

### Tests d'intégration

```bash
flutter test integration_test
```

## 🐛 Dépannage

### Erreur : "Unable to find assets"

Assurez-vous que le fichier `.env` est bien dans le dossier `mobile-app` et que `pubspec.yaml` inclut :

```yaml
flutter:
  assets:
    - .env
```

### Erreur de connexion API

1. Vérifiez que le backend est démarré
2. Vérifiez l'URL dans `.env`
3. Testez l'API avec curl ou Postman
4. Vérifiez les logs du backend pour les erreurs CORS

### Erreur : "No devices found"

1. Démarrez un émulateur Android ou iOS
2. Connectez un appareil physique avec le mode développeur activé
3. Vérifiez avec `flutter devices`

### Erreur de build

```bash
flutter clean
flutter pub get
flutter run
```

## 📚 Ressources

- Documentation Flutter : https://flutter.dev/docs
- Documentation Dio (HTTP client) : https://pub.dev/packages/dio
- Documentation Riverpod : https://riverpod.dev

## 🔐 Sécurité

- Les tokens sont stockés de manière sécurisée avec `flutter_secure_storage`
- Les tokens expirent automatiquement (30 min pour access, 7 jours pour refresh)
- Le rafraîchissement automatique des tokens est implémenté

## 📝 Notes

- L'application utilise Riverpod pour la gestion d'état
- La navigation utilise GoRouter
- Les requêtes API incluent automatiquement le token d'authentification
- Les erreurs 401 redirigent automatiquement vers la page de connexion

