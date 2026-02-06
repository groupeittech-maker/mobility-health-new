# ⚡ Commandes Rapides - Application Mobile

## 🚀 Lancer l'Application

### Méthode 1 : Script Automatique (Recommandé)

**Windows (PowerShell)** :
```powershell
cd mobile-app
.\lancer.ps1
```

**Windows (CMD)** :
```cmd
cd mobile-app
lancer.bat
```

### Méthode 2 : Commandes Manuelles

```powershell
# 1. Aller dans le dossier mobile-app
cd mobile-app

# 2. Voir les appareils disponibles
flutter devices

# 3. Lancer l'application
flutter run
```

### Méthode 3 : Sur un Appareil Spécifique

```powershell
cd mobile-app
flutter run -d R5CX62DGYHD
```

## 📋 Commandes Utiles

### Voir les Appareils
```powershell
flutter devices
```

### Nettoyer le Projet
```powershell
flutter clean
flutter pub get
```

### Vérifier l'Installation
```powershell
flutter doctor
```

### Analyser le Code
```powershell
flutter analyze
```

### Hot Reload (pendant l'exécution)
Appuyez sur `r` dans le terminal

### Hot Restart
Appuyez sur `R` (majuscule) dans le terminal

### Quitter
Appuyez sur `q` dans le terminal

## ⚠️ Erreur : "No pubspec.yaml file found"

**Solution** : Vous n'êtes pas dans le dossier `mobile-app`

```powershell
# Vérifiez votre répertoire actuel
Get-Location

# Changez de répertoire
cd mobile-app

# Vérifiez que pubspec.yaml existe
Test-Path pubspec.yaml
```

## 📝 Checklist Avant de Lancer

- [ ] Être dans le dossier `mobile-app`
- [ ] Backend démarré sur `0.0.0.0:8000`
- [ ] Fichier `.env` configuré
- [ ] Appareil Android connecté ou émulateur démarré
- [ ] Dépendances installées (`flutter pub get`)

## 🎯 Commande Complète en Une Ligne

```powershell
cd "D:\logiciel et application\Mobility Health\mobile-app" ; flutter run
```

