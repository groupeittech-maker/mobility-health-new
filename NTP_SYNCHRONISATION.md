# 🔧 Guide de Synchronisation NTP - Mobility Health

## ⚠️ Problème : "Request has expired" - Mauvaise heure sur serveur

Si vous rencontrez des erreurs `AccessDenied` avec le message "Request has expired" pour les URLs signées Minio, cela peut être dû à une **mauvaise synchronisation de l'heure** sur le serveur.

## 🔍 Diagnostic

### 1. Vérifier l'heure du serveur

**Via l'API :**
```bash
curl http://localhost:8000/health
```

La réponse devrait inclure :
```json
{
  "status": "healthy",
  "server_time_utc": "2024-12-02T10:30:00.123456",
  "time_valid": true,
  "warning": null
}
```

Si `time_valid` est `false`, l'heure du serveur est incorrecte.

**Via la ligne de commande (Linux) :**
```bash
date
date -u  # UTC
timedatectl status  # Vérifier la synchronisation NTP
```

**Via PowerShell (Windows) :**
```powershell
Get-Date
Get-Date -Format "yyyy-MM-dd HH:mm:ss UTC" -AsUTC
w32tm /query /status  # Vérifier la synchronisation NTP
```

### 2. Comparer avec l'heure réelle

Comparez l'heure du serveur avec l'heure UTC réelle :
- **Heure UTC réelle** : https://www.timeanddate.com/worldclock/timezone/utc
- **Heure serveur** : Voir ci-dessus

Si la différence est supérieure à quelques secondes, il y a un problème de synchronisation.

## ✅ Solutions

### Solution 1 : Synchronisation NTP automatique (Recommandé)

#### Sur Linux (Ubuntu/Debian)

```bash
# Installer NTP si ce n'est pas déjà fait
sudo apt-get update
sudo apt-get install ntp -y

# Vérifier que NTP est actif
sudo systemctl status ntp

# Si NTP n'est pas actif, le démarrer
sudo systemctl start ntp
sudo systemctl enable ntp

# Forcer une synchronisation immédiate
sudo ntpdate -s time.nist.gov

# Ou avec systemd-timesyncd (Ubuntu 16.04+)
sudo timedatectl set-ntp true
sudo systemctl restart systemd-timesyncd
```

#### Sur Windows Server

```powershell
# Vérifier le statut de la synchronisation
w32tm /query /status

# Configurer pour synchroniser automatiquement
w32tm /config /manualpeerlist:"time.windows.com,time.nist.gov" /syncfromflags:manual /reliable:YES /update

# Redémarrer le service
net stop w32time
net start w32time

# Forcer une synchronisation immédiate
w32tm /resync /force
```

#### Sur Docker

Si vous utilisez Docker, le conteneur hérite de l'heure de l'hôte. Vérifiez l'heure de l'hôte :

```bash
# Sur l'hôte
date -u

# Dans le conteneur
docker exec mobility_health_api date -u
```

Si l'heure est différente, synchronisez l'hôte (voir ci-dessus).

### Solution 2 : Correction manuelle de l'heure (Temporaire)

⚠️ **Attention** : Cette solution est temporaire. Configurez NTP pour une synchronisation automatique.

#### Sur Linux

```bash
# Définir l'heure manuellement (remplacez par l'heure actuelle)
sudo date -s "2024-12-02 10:30:00"

# Ou avec timedatectl
sudo timedatectl set-time "2024-12-02 10:30:00"
```

#### Sur Windows

```powershell
# Définir l'heure manuellement
Set-Date -Date "2024-12-02 10:30:00"
```

### Solution 3 : Vérifier la configuration NTP

#### Fichiers de configuration NTP (Linux)

```bash
# Fichier de configuration principal
cat /etc/ntp.conf

# Vérifier les serveurs NTP configurés
grep "^server" /etc/ntp.conf

# Tester la connexion aux serveurs NTP
ntpq -p
```

#### Configuration recommandée pour `/etc/ntp.conf` :

```
# Serveurs NTP publics
server 0.pool.ntp.org
server 1.pool.ntp.org
server 2.pool.ntp.org
server 3.pool.ntp.org

# Serveurs NTP locaux (si disponibles)
# server ntp.example.com
```

## 🔄 Redémarrer les services après correction

Après avoir corrigé l'heure, redémarrez le serveur backend :

```bash
# Si vous utilisez systemd
sudo systemctl restart mobility-health-api

# Si vous utilisez Docker
docker-compose restart api

# Si vous utilisez uvicorn directement
# Arrêtez et redémarrez le serveur
```

## 📊 Vérification continue

### Script de vérification automatique

Créez un script pour vérifier régulièrement l'heure :

```bash
#!/bin/bash
# check_time.sh

SERVER_TIME=$(date -u +%s)
REAL_TIME=$(curl -s http://worldtimeapi.org/api/timezone/Etc/UTC | grep -oP '"unixtime":\K[0-9]+')
DIFF=$((SERVER_TIME - REAL_TIME))

if [ $DIFF -gt 5 ] || [ $DIFF -lt -5 ]; then
    echo "⚠️  ATTENTION: L'heure du serveur est décalée de $DIFF secondes"
    echo "Synchronisation NTP recommandée"
    exit 1
else
    echo "✅ Heure du serveur synchronisée (différence: $DIFF secondes)"
    exit 0
fi
```

### Cron job pour vérification automatique

```bash
# Ajouter à crontab (crontab -e)
# Vérifier l'heure toutes les heures
0 * * * * /path/to/check_time.sh
```

## 🎯 Impact sur les URLs signées

Les URLs signées Minio sont valides pendant **2 heures** à partir de leur génération. Si l'heure du serveur est incorrecte :

- **Heure en avance** : Les URLs peuvent être rejetées par Minio comme "expirées" avant leur expiration réelle
- **Heure en retard** : Les URLs peuvent être acceptées après leur expiration réelle (problème de sécurité)

**Solution implémentée** : Les URLs sont maintenant générées **à la volée** à chaque requête, ce qui évite le problème même si l'heure est légèrement décalée. Cependant, il est toujours recommandé d'avoir une heure correcte pour d'autres fonctionnalités.

## 📝 Notes importantes

1. **Toujours utiliser UTC** : Le serveur doit être configuré en UTC pour éviter les problèmes de fuseau horaire
2. **Synchronisation automatique** : Configurez NTP pour une synchronisation automatique, ne corrigez pas manuellement
3. **Vérification régulière** : Vérifiez régulièrement que l'heure est correcte
4. **Logs** : Les logs du serveur incluent maintenant l'heure UTC pour faciliter le diagnostic

## 🔗 Ressources

- [NTP Pool Project](https://www.ntppool.org/)
- [Time and Date UTC](https://www.timeanddate.com/worldclock/timezone/utc)
- [Minio Presigned URLs Documentation](https://docs.min.io/docs/javascript-client-api-reference.html#presignedGetObject)

