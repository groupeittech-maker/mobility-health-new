# 🚀 Lancer l'Application - Guide Rapide

## ⚡ Commande Rapide

**Depuis le dossier `mobile-app`** :

```powershell
cd mobile-app
flutter run
```

Ou pour choisir un appareil spécifique :

```powershell
cd mobile-app
flutter devices          # Voir les appareils disponibles
flutter run -d <device-id>
```

## 📋 Étapes Complètes

### 1. Vérifier que vous êtes dans le bon dossier

```powershell
# Vous devez être ici :
cd "D:\logiciel et application\Mobility Health\mobile-app"
```

### 2. Vérifier que le backend est démarré

Dans un **autre terminal**, démarrez le backend :

```powershell
cd "D:\logiciel et application\Mobility Health"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Vérifier le fichier .env

Le fichier `mobile-app/.env` doit contenir :

```env
API_BASE_URL=http://172.16.202.81:8000/api/v1
```

### 4. Lancer l'application

```powershell
# Depuis mobile-app
flutter run
```

Flutter vous demandera de choisir un appareil si plusieurs sont disponibles.

## 🎯 Commandes Utiles

### Voir les appareils disponibles
```powershell
flutter devices
```

### Lancer sur un appareil spécifique
```powershell
flutter run -d R5CX62DGYHD
```

### Hot Reload (pendant l'exécution)
Appuyez sur `r` dans le terminal

### Hot Restart
Appuyez sur `R` (majuscule) dans le terminal

### Quitter
Appuyez sur `q` dans le terminal

## 🐛 Erreurs Courantes

### "No pubspec.yaml file found"
**Solution** : Vous n'êtes pas dans le dossier `mobile-app`
```powershell
cd mobile-app
```

### "No supported devices connected"
**Solution** : Le projet n'a pas été initialisé pour Android
```powershell
flutter create . --platforms=android
```

### Erreur de connexion API
**Solution** : Vérifiez que le backend est démarré avec `--host 0.0.0.0`

## ✅ Checklist Avant de Lancer

- [ ] Être dans le dossier `mobile-app`
- [ ] Backend démarré sur `0.0.0.0:8000`
- [ ] Fichier `.env` configuré
- [ ] Appareil Android connecté ou émulateur démarré
- [ ] Dépendances installées (`flutter pub get`)

