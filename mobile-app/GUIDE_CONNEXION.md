# Guide de Connexion - Application Mobile Mobility Health

Ce guide vous explique comment vous connecter à l'application mobile.

## 📱 Processus de Connexion

### Option 1 : Se Connecter avec un Compte Existant

1. **Lancer l'application**
   - Ouvrez l'application Mobility Health sur votre appareil
   - L'écran de démarrage (Splash) s'affiche automatiquement

2. **Accéder à la page de connexion**
   - Si vous n'êtes pas connecté, vous serez automatiquement redirigé vers la page de connexion
   - Sinon, depuis l'écran d'accueil, cliquez sur "Se connecter"

3. **Saisir vos identifiants**
   - **Nom d'utilisateur** : Entrez votre nom d'utilisateur
   - **Mot de passe** : Entrez votre mot de passe
   - Vous pouvez cliquer sur l'icône 👁️ pour afficher/masquer le mot de passe

4. **Se connecter**
   - Cliquez sur le bouton "Se connecter"
   - Un indicateur de chargement apparaît pendant la connexion
   - Si la connexion réussit, vous serez redirigé vers l'écran d'accueil

5. **En cas d'erreur**
   - Vérifiez que votre nom d'utilisateur et mot de passe sont corrects
   - Vérifiez que le backend est en cours d'exécution
   - Vérifiez votre connexion internet
   - Vérifiez la configuration de l'URL API dans le fichier `.env`

---

### Option 2 : Créer un Nouveau Compte (Inscription)

1. **Accéder à la page d'inscription**
   - Depuis la page de connexion, cliquez sur "S'inscrire" en bas de l'écran
   - Ou accédez directement à l'écran d'inscription

2. **Remplir le formulaire d'inscription**
   - **Email** : Entrez votre adresse email (ex: `user@example.com`)
   - **Nom d'utilisateur** : Choisissez un nom d'utilisateur unique (minimum 3 caractères)
   - **Nom complet** : Votre nom complet (optionnel)
   - **Mot de passe** : Choisissez un mot de passe sécurisé (minimum 8 caractères)
   - **Confirmer le mot de passe** : Retapez votre mot de passe

3. **Valider l'inscription**
   - Cliquez sur le bouton "S'inscrire"
   - Si l'inscription réussit, vous serez automatiquement connecté et redirigé vers l'écran d'accueil

4. **En cas d'erreur**
   - Vérifiez que l'email n'est pas déjà utilisé
   - Vérifiez que le nom d'utilisateur n'est pas déjà pris
   - Vérifiez que le mot de passe respecte les critères (minimum 8 caractères)
   - Vérifiez que les deux mots de passe correspondent

---

## 🔑 Identifiants de Test

Si vous avez des identifiants de test dans votre backend, vous pouvez les utiliser :

### Exemple d'identifiants (à adapter selon votre configuration)

```
Nom d'utilisateur : testuser
Mot de passe : testpassword123
```

**Note** : Consultez le fichier `IDENTIFIANTS_TEST.md` à la racine du projet pour les identifiants de test spécifiques à votre environnement.

---

## ⚙️ Configuration Préalable

Avant de vous connecter, assurez-vous que :

### 1. Le Backend est Démarré

Le backend FastAPI doit être en cours d'exécution :

```bash
# Depuis la racine du projet
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Ou utilisez les scripts :

```bash
# Windows
.\scripts\start_backend.ps1

# Linux/Mac
./scripts/start_backend.sh
```

### 2. L'URL API est Configurée

Vérifiez que le fichier `.env` dans `mobile-app/` contient la bonne URL.

**Backend de production (Hostinger)** :

```env
API_BASE_URL=https://srv1324425.hstgr.cloud/api/v1
API_CONNEXION_BACKEND=https://srv1324425.hstgr.cloud
```

**Pour le développement local** :

- **Android Emulator** : `http://10.0.2.2:8000/api/v1`
- **iOS Simulator** : `http://localhost:8000/api/v1`
- **Appareil physique** : IP de votre machine (ex: `http://192.168.1.100:8000/api/v1`)

### 3. Les Permissions sont Accordées

Pour certaines fonctionnalités (comme SOS avec géolocalisation), l'application demandera des permissions :
- **Localisation** : Nécessaire pour les alertes SOS
- **Stockage** : Pour sauvegarder les documents téléchargés

---

## 🔄 Après la Connexion

Une fois connecté, vous pouvez :

1. **Accéder à l'écran d'accueil** avec toutes les fonctionnalités
2. **Voir vos informations** dans le profil
3. **Accéder aux fonctionnalités** :
   - Produits d'assurance
   - Mes souscriptions
   - Mes attestations
   - Alerte SOS
   - Et plus encore...

---

## 🔐 Gestion de la Session

### Connexion Automatique

- Si vous vous êtes déjà connecté, l'application se souvient de votre session
- Au démarrage, si votre token est encore valide, vous serez automatiquement connecté
- Si le token a expiré, l'application tentera de le rafraîchir automatiquement

### Déconnexion

Pour vous déconnecter :
1. Allez sur l'écran d'accueil
2. Cliquez sur l'icône de déconnexion (👤) en haut à droite
3. Confirmez la déconnexion

---

## 🐛 Dépannage

### Erreur : "Impossible de se connecter au serveur"

**Solutions** :
1. Vérifiez que le backend est démarré
2. Vérifiez l'URL dans `.env`
3. Vérifiez votre connexion internet
4. Pour Android Emulator, utilisez `10.0.2.2` au lieu de `localhost`

### Erreur : "Incorrect username or password"

**Solutions** :
1. Vérifiez que vous utilisez les bons identifiants
2. Essayez de créer un nouveau compte
3. Vérifiez que l'utilisateur existe dans la base de données du backend

### Erreur : "User is inactive"

**Solutions** :
1. L'utilisateur a été désactivé dans le backend
2. Contactez un administrateur pour réactiver le compte

### L'application ne se connecte pas

**Solutions** :
1. Vérifiez les logs du backend pour voir les erreurs
2. Vérifiez la configuration CORS dans le backend
3. Vérifiez que le port 8000 n'est pas bloqué par un firewall
4. Testez l'API directement avec Postman ou curl

---

## 📞 Support

Si vous rencontrez des problèmes de connexion :

1. Vérifiez les logs de l'application (console Flutter)
2. Vérifiez les logs du backend
3. Consultez le fichier `TROUBLESHOOTING.md` dans le projet
4. Vérifiez que toutes les dépendances sont installées (`flutter pub get`)

---

## 🔒 Sécurité

- Les mots de passe sont stockés de manière sécurisée (hashés côté serveur)
- Les tokens d'authentification sont stockés de manière chiffrée sur l'appareil
- Les tokens expirent automatiquement (30 minutes pour access token, 7 jours pour refresh token)
- Le rafraîchissement automatique des tokens est géré par l'application

---

## 📝 Notes Importantes

1. **Première connexion** : Si c'est votre première fois, créez un compte via l'option "S'inscrire"

2. **Mot de passe oublié** : La fonctionnalité de réinitialisation du mot de passe sera disponible prochainement

3. **Comptes multiples** : Vous pouvez vous déconnecter et vous connecter avec un autre compte

4. **Mode hors ligne** : L'application nécessite une connexion internet pour se connecter

---

**Dernière mise à jour** : Basé sur l'implémentation actuelle de l'application


