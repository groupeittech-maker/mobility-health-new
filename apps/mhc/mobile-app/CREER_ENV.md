# Comment créer le fichier .env

Le fichier `.env` est nécessaire pour configurer l'URL de l'API. Voici comment le créer.

## 🚀 Méthode Rapide (Recommandée)

### Windows (PowerShell)

1. Ouvrez PowerShell dans le dossier `mobile-app`
2. Exécutez le script :
   ```powershell
   .\create_env.ps1
   ```

### Linux/Mac

1. Ouvrez un terminal dans le dossier `mobile-app`
2. Rendez le script exécutable et exécutez-le :
   ```bash
   chmod +x create_env.sh
   ./create_env.sh
   ```

---

## 📝 Méthode Manuelle

### Option 1 : Créer le fichier directement

1. **Créez un nouveau fichier** nommé `.env` dans le dossier `mobile-app`

2. **Copiez-collez ce contenu** :

```env
# Configuration API
API_BASE_URL=http://localhost:8000/api/v1
API_TIMEOUT=30000

# Environment
ENVIRONMENT=development

# App Configuration
APP_NAME=Mobility Health
APP_VERSION=1.0.0
```

3. **Sauvegardez le fichier**

### Option 2 : Copier depuis .env.example

Si le fichier `.env.example` existe :

**Windows (PowerShell)** :
```powershell
Copy-Item .env.example .env
```

**Linux/Mac** :
```bash
cp .env.example .env
```

---

## ⚙️ Configuration selon votre environnement

Après avoir créé le fichier `.env`, **modifiez l'URL API** selon votre environnement :

### Pour Android Emulator

```env
API_BASE_URL=http://10.0.2.2:8000/api/v1
```

### Pour iOS Simulator

```env
API_BASE_URL=http://localhost:8000/api/v1
```

### Pour Appareil Physique

1. Trouvez l'adresse IP de votre machine :
   - **Windows** : Ouvrez PowerShell et tapez `ipconfig` (cherchez "IPv4")
   - **Mac/Linux** : Ouvrez Terminal et tapez `ifconfig` ou `ip addr`

2. Utilisez cette IP dans le fichier `.env` :
   ```env
   API_BASE_URL=http://192.168.1.XXX:8000/api/v1
   ```
   (Remplacez XXX par votre adresse IP)

---

## ✅ Vérification

Pour vérifier que le fichier est bien créé :

**Windows** :
```powershell
Get-Content .env
```

**Linux/Mac** :
```bash
cat .env
```

Vous devriez voir le contenu du fichier.

---

## 🔒 Sécurité

⚠️ **Important** : Le fichier `.env` contient des configurations sensibles et ne doit **jamais** être commité dans Git. Il est déjà dans `.gitignore`.

---

## 🐛 Problèmes courants

### Le fichier n'apparaît pas dans l'explorateur de fichiers

Les fichiers commençant par un point (`.`) sont souvent cachés par défaut :

- **Windows** : Dans l'explorateur, allez dans "Affichage" → Cochez "Éléments masqués"
- **VS Code** : Les fichiers `.env` devraient apparaître normalement

### Erreur "File not found" lors de l'exécution

Assurez-vous que vous êtes dans le bon dossier :
```bash
# Vérifiez que vous êtes dans mobile-app
pwd  # Linux/Mac
Get-Location  # Windows PowerShell
```

---

## 📞 Besoin d'aide ?

Si vous rencontrez des problèmes :
1. Vérifiez que vous êtes dans le dossier `mobile-app`
2. Vérifiez que le fichier `.env` existe bien
3. Vérifiez le contenu du fichier avec `cat .env` ou `Get-Content .env`


