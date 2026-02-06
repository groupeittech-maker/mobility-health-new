# Comment résoudre les problèmes de cache du navigateur

## Problème
Les modifications apportées aux fichiers HTML, CSS ou JavaScript ne sont pas visibles dans le navigateur car elles sont mises en cache.

## Solutions

### Solution 1 : Utiliser le serveur avec désactivation du cache (Recommandé)

Le serveur Python personnalisé (`server.py`) désactive automatiquement le cache :

```powershell
cd frontend-simple
python server.py
```

Ou utilisez le script :
```powershell
.\scripts\start_frontend.ps1
```

### Solution 2 : Forcer le rechargement dans le navigateur

**Windows/Linux :**
- `Ctrl + F5` : Rechargement complet sans cache
- `Ctrl + Shift + R` : Rechargement complet sans cache
- `F12` → Onglet Network → Cocher "Disable cache"

**Mac :**
- `Cmd + Shift + R` : Rechargement complet sans cache
- `Cmd + Option + E` : Vider le cache et recharger

### Solution 3 : Vider le cache manuellement

**Chrome/Edge :**
1. Appuyez sur `F12` pour ouvrir les outils de développement
2. Clic droit sur le bouton de rechargement (🔄)
3. Sélectionnez "Vider le cache et actualiser de force"

**Firefox :**
1. `Ctrl + Shift + Delete` (Windows) ou `Cmd + Shift + Delete` (Mac)
2. Sélectionnez "Cache" et "Tout"
3. Cliquez sur "Effacer maintenant"

### Solution 4 : Mode Navigation privée

Ouvrez votre page en mode navigation privée pour éviter le cache :
- **Chrome/Edge** : `Ctrl + Shift + N`
- **Firefox** : `Ctrl + Shift + P`

## Vérification

Pour vérifier que vos modifications sont prises en compte :

1. Modifiez un fichier (HTML, CSS ou JS)
2. Sauvegardez le fichier
3. Dans le navigateur :
   - Appuyez sur `Ctrl + F5` (ou `Cmd + Shift + R` sur Mac)
   - Ou utilisez les outils de développement (F12) avec "Disable cache" activé

## Note pour le développement

Pour le développement, il est recommandé de :
- Utiliser le serveur `server.py` qui désactive le cache automatiquement
- Activer "Disable cache" dans les outils de développement du navigateur (F12)
- Utiliser un rechargement forcé (`Ctrl + F5`) après chaque modification importante

