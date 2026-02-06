# Guide pour Lancer l'Application Mobile

## 📋 Prérequis

1. ✅ Flutter SDK installé
2. ✅ Backend démarré et accessible
3. ✅ Fichier `.env` configuré

## 🚀 Étapes pour Lancer l'Application

### Étape 1 : Vérifier que le Backend est Démarré

Le backend doit être en cours d'exécution et accessible depuis votre appareil mobile.

**Démarrer le backend** (depuis la racine du projet) :

```bash
# Windows PowerShell
cd ..
.\scripts\start_backend.ps1

# Ou manuellement
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

⚠️ **Important** : Le backend doit écouter sur `0.0.0.0` (toutes les interfaces) et non seulement sur `localhost` pour être accessible depuis un appareil mobile.

### Étape 2 : Vérifier la Configuration .env

Vérifiez que votre fichier `.env` dans `mobile-app/` contient la bonne URL :

```env
API_BASE_URL=http://172.16.202.81:8000/api/v1
```

**Pour trouver votre IP** :
- Windows : `ipconfig` (cherchez "IPv4")
- L'IP doit correspondre à celle de votre machine sur le réseau local

### Étape 3 : Installer les Dépendances Flutter

```bash
cd mobile-app
flutter pub get
```

### Étape 4 : Vérifier les Appareils Disponibles

```bash
flutter devices
```

Vous devriez voir :
- Un émulateur Android/iOS
- Ou un appareil physique connecté

### Étape 5 : Lancer l'Application

#### Option A : Lancer sur un Appareil/Émulateur Spécifique

```bash
flutter run -d <device-id>
```

#### Option B : Lancer et Choisir l'Appareil

```bash
flutter run
```

Flutter vous demandera de choisir un appareil si plusieurs sont disponibles.

#### Option C : Mode Debug (avec Hot Reload)

```bash
flutter run --debug
```

#### Option D : Mode Release (Performance Optimale)

```bash
flutter run --release
```

## 🔧 Dépannage

### Erreur : "Not Found" ou "Connection refused"

**Solutions** :

1. **Vérifier que le backend est démarré** :
   ```bash
   # Testez l'API dans un navigateur
   http://172.16.202.81:8000/api/v1
   # Devrait retourner une erreur 404 (normal) ou un message JSON
   ```

2. **Vérifier que le backend écoute sur toutes les interfaces** :
   - Le backend doit être démarré avec `--host 0.0.0.0`
   - Pas seulement `--host localhost` ou `--host 127.0.0.1`

3. **Vérifier le firewall** :
   - Windows : Autorisez le port 8000 dans le firewall
   - Vérifiez que le port 8000 n'est pas bloqué

4. **Vérifier l'URL dans .env** :
   - L'IP doit correspondre à celle de votre machine
   - Testez avec `ping 172.16.202.81` depuis votre appareil mobile

### Erreur : "No devices found"

**Solutions** :

1. **Pour Android** :
   - Démarrez un émulateur Android depuis Android Studio
   - Ou connectez un appareil Android avec USB Debugging activé

2. **Pour iOS** (Mac uniquement) :
   - Démarrez un simulateur iOS depuis Xcode
   - Ou connectez un iPhone avec Xcode configuré

### Erreur : "Package not found" ou erreurs de dépendances

**Solutions** :

```bash
flutter clean
flutter pub get
flutter run
```

### L'application se lance mais ne peut pas se connecter

**Vérifications** :

1. Testez l'API avec curl ou Postman :
   ```bash
   curl http://172.16.202.81:8000/api/v1
   ```

2. Vérifiez les logs du backend pour voir les requêtes

3. Vérifiez la configuration CORS dans le backend

## 📱 Commandes Utiles

### Voir les Logs en Temps Réel

```bash
flutter run --verbose
```

### Hot Reload (pendant l'exécution)

Appuyez sur `r` dans le terminal où l'app s'exécute

### Hot Restart

Appuyez sur `R` (majuscule) dans le terminal

### Quitter l'Application

Appuyez sur `q` dans le terminal

### Voir les Appareils Disponibles

```bash
flutter devices
```

### Nettoyer le Projet

```bash
flutter clean
```

## 🎯 Test Rapide

1. **Démarrer le backend** :
   ```bash
   cd ..
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Tester l'API** (dans un navigateur) :
   ```
   http://172.16.202.81:8000/api/v1
   ```

3. **Lancer l'app** :
   ```bash
   cd mobile-app
   flutter run
   ```

4. **Se connecter** avec :
   - Username : `user`
   - Password : `user123`

## ✅ Checklist Avant de Lancer

- [ ] Backend démarré sur `0.0.0.0:8000`
- [ ] Fichier `.env` configuré avec la bonne IP
- [ ] Dépendances Flutter installées (`flutter pub get`)
- [ ] Appareil/émulateur disponible (`flutter devices`)
- [ ] Port 8000 accessible (pas bloqué par firewall)
- [ ] Backend accessible depuis le navigateur

## 🐛 Si Rien ne Fonctionne

1. Vérifiez les logs du backend
2. Vérifiez les logs Flutter (`flutter run --verbose`)
3. Testez l'API directement avec Postman ou curl
4. Vérifiez que vous êtes sur le même réseau WiFi (pour appareil physique)


