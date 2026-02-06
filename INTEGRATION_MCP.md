# Guide d'intégration du serveur MCP dans Mobility Health

Ce guide explique comment utiliser le serveur MCP pour les statistiques dans votre application Mobility Health.

## ✅ Fichiers créés

1. **Backend (FastAPI)** :
   - `app/api/v1/stats.py` - Endpoint API pour les statistiques

2. **Frontend** :
   - `frontend-simple/js/stats.js` - Module JavaScript pour les statistiques
   - `frontend-simple/stats-dashboard.html` - Page de tableau de bord des statistiques

## 🚀 Démarrage rapide

### 1. Démarrer le serveur MCP

Dans le répertoire du serveur MCP :

```bash
cd "D:\logiciel et application\serveur MCP"
python server_rest.py
```

Le serveur MCP sera accessible sur `http://localhost:5000`

### 2. Configurer l'URL du serveur MCP (optionnel)

Par défaut, l'API Mobility Health cherche le serveur MCP à `http://localhost:5000`.

Pour changer l'URL, ajoutez dans le fichier `.env` de Mobility Health :

```env
MCP_SERVER_URL=http://localhost:5000
```

### 3. Démarrer l'application Mobility Health

```bash
cd "D:\logiciel et application\Mobility Health"
uvicorn app.main:app --reload
```

### 4. Accéder à la page des statistiques

Ouvrez dans votre navigateur :
```
http://localhost:8000/frontend-simple/stats-dashboard.html
```

Ou intégrez le lien dans votre menu de navigation.

## 📡 Endpoints API disponibles

### POST `/api/v1/stats/query`

Interroge le serveur MCP avec une requête en langage naturel.

**Requête :**
```json
{
  "query": "Montre-moi mes statistiques de course",
  "user_id": 1  // optionnel, utilise l'utilisateur connecté par défaut
}
```

**Réponse :**
```json
{
  "query": "Montre-moi mes statistiques de course",
  "sql_query": "SELECT ...",
  "charts": [...],
  "interpretation_text": "Analyse des données...",
  "summary": {...},
  "data_count": 10,
  "raw_data": [...]
}
```

### GET `/api/v1/stats/schema`

Récupère le schéma de la base de données depuis le serveur MCP.

### GET `/api/v1/stats/health`

Vérifie que le serveur MCP est accessible.

## 💻 Utilisation dans le code JavaScript

### Exemple basique

```javascript
// Charger le module stats.js
<script src="js/stats.js"></script>

// Faire une requête
const result = await queryStatistics("Montre-moi mes statistiques d'activité");

// Afficher les graphiques
displayCharts(result.charts, 'charts-container');

// Afficher l'interprétation
displayInterpretation(result.interpretation_text, 'interpretation-container');

// Afficher le résumé
displaySummary(result.summary, 'summary-container');
```

### Exemple avec gestion d'erreurs

```javascript
try {
    const result = await queryStatistics("Combien de calories ai-je brûlées?");
    
    // Traiter les résultats
    console.log('Graphiques:', result.charts);
    console.log('Interprétation:', result.interpretation_text);
    
    // Afficher
    displayCharts(result.charts);
    displayInterpretation(result.interpretation_text);
    
} catch (error) {
    console.error('Erreur:', error);
    alert('Erreur lors de la récupération des statistiques: ' + error.message);
}
```

## 🔗 Intégration dans d'autres pages

### Ajouter un lien dans le menu

Dans votre fichier de navigation, ajoutez :

```html
<li class="nav-item">
    <a class="nav-link" href="stats-dashboard.html">
        📊 Statistiques
    </a>
</li>
```

### Ajouter un widget dans le tableau de bord

Dans `user-dashboard.html` ou `admin-dashboard.html`, ajoutez :

```html
<div class="card">
    <div class="card-header">
        <h5>Statistiques rapides</h5>
    </div>
    <div class="card-body">
        <input type="text" id="quickQuery" class="form-control mb-2" 
               placeholder="Ex: Mes statistiques cette semaine">
        <button class="btn btn-primary" onclick="quickStats()">Rechercher</button>
        <div id="quickStatsResult" class="mt-3"></div>
    </div>
</div>

<script src="js/stats.js"></script>
<script>
async function quickStats() {
    const query = document.getElementById('quickQuery').value;
    if (!query) return;
    
    try {
        const result = await queryStatistics(query);
        document.getElementById('quickStatsResult').innerHTML = 
            `<p>${result.interpretation_text}</p>`;
    } catch (error) {
        document.getElementById('quickStatsResult').innerHTML = 
            `<p class="text-danger">Erreur: ${error.message}</p>`;
    }
}
</script>
```

## 🔐 Authentification

Tous les endpoints nécessitent une authentification. Le token est automatiquement récupéré depuis `localStorage` ou via la fonction `getStoredAccessToken()` de `api.js`.

## 📊 Exemples de requêtes

- "Montre-moi mes statistiques d'activité"
- "Combien de calories ai-je brûlées cette semaine?"
- "Compare mes activités de marche et de course"
- "Montre-moi l'évolution de mon activité sur les 30 derniers jours"
- "Quel est mon poids moyen ce mois-ci?"
- "Quelles sont mes activités les plus fréquentes?"

## 🛠️ Dépannage

### Le serveur MCP n'est pas accessible

1. Vérifiez que le serveur MCP est démarré :
   ```bash
   cd "D:\logiciel et application\serveur MCP"
   python server_rest.py
   ```

2. Vérifiez l'URL dans `.env` :
   ```env
   MCP_SERVER_URL=http://localhost:5000
   ```

3. Testez la connexion :
   ```bash
   curl http://localhost:5000/health
   ```

### Erreur 401 (Non autorisé)

- Vérifiez que vous êtes connecté dans l'application
- Vérifiez que le token d'accès est valide
- Reconnectez-vous si nécessaire

### Les graphiques ne s'affichent pas

- Vérifiez que Plotly est chargé (inclus dans `stats-dashboard.html`)
- Vérifiez la console du navigateur pour les erreurs JavaScript
- Vérifiez que les données sont retournées correctement

### Timeout

- Le serveur MCP peut prendre du temps si Ollama n'est pas installé
- Augmentez le timeout dans `stats.py` si nécessaire
- Installez Ollama pour de meilleures performances

## 📝 Notes importantes

1. **Base de données** : Le serveur MCP utilise sa propre base de données SQLite. Pour utiliser les données de Mobility Health, vous devrez :
   - Soit connecter le serveur MCP à la base PostgreSQL de Mobility Health
   - Soit synchroniser les données entre les deux bases

2. **Performance** : Les requêtes peuvent prendre quelques secondes, surtout si Ollama n'est pas installé.

3. **Sécurité** : En production, ajoutez :
   - Validation des requêtes utilisateur
   - Limitation du taux de requêtes
   - Authentification renforcée

## 🔄 Prochaines étapes

1. **Connecter à la base PostgreSQL de Mobility Health** :
   Modifiez `database.py` dans le serveur MCP pour utiliser la même base que Mobility Health.

2. **Ajouter des types d'activités spécifiques** :
   Adaptez `models.py` et `nlp_interpreter.py` pour vos types d'activités.

3. **Personnaliser les graphiques** :
   Modifiez `visualization.py` pour ajouter vos types de visualisations.

4. **Ajouter des métriques spécifiques** :
   Adaptez le schéma pour inclure vos métriques de santé.

