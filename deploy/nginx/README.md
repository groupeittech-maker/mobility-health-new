# Nginx + HTTPS pour Mobility Health API

## 1. Installer Nginx sur le VPS

```bash
sudo apt-get update
sudo apt-get install -y nginx
```

## 2. Installer le fichier de configuration

- Copier `mobility-health.conf` vers le serveur (ou le contenu depuis le dépôt).
- Remplacer **DOMAINE** par ton domaine (ex: `srv1324425.hstgr.cloud` ou `mobility-health.ittechmed.com`).

```bash
sudo cp mobility-health.conf /etc/nginx/sites-available/mobility-health.conf
sudo sed -i 's/DOMAINE/srv1324425.hstgr.cloud/g' /etc/nginx/sites-available/mobility-health.conf
sudo ln -sf /etc/nginx/sites-available/mobility-health.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## 3. Ouvrir le port 80 (et 443 pour HTTPS)

```bash
sudo ufw allow 80
sudo ufw allow 443
sudo ufw status
```

## 4. Obtenir un certificat SSL (Let's Encrypt)

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo mkdir -p /var/www/certbot
# Obtenir le certificat (remplacer srv1324425.hstgr.cloud par ton domaine)
sudo certbot certonly --webroot -w /var/www/certbot -d srv1324425.hstgr.cloud --email ton@email.com --agree-tos --no-eff-email
```

Puis décommenter le bloc HTTPS dans `/etc/nginx/sites-available/mobility-health.conf`, remplacer `DOMAINE` par ton domaine dans les chemins `ssl_certificate`, et recharger Nginx :

```bash
sudo nginx -t && sudo systemctl reload nginx
```

Renouvellement automatique :

```bash
sudo certbot renew --dry-run
```

---

## Caméra (photo médicale)

Si la caméra ne fonctionne pas sur les pages `product-selection.html` ou `forms-medical.html`, ajoutez l'en-tête **Permissions-Policy** dans le bloc server qui sert le frontend :

```nginx
add_header Permissions-Policy "camera=(self)" always;
add_header Feature-Policy "camera 'self'" always;
```

Ou inclure le snippet :

```nginx
include /chemin/vers/deploy/nginx/permissions-policy-camera.conf;
```

Vérifier que le site est bien en **HTTPS** (obligatoire pour `getUserMedia`).

---

# Tests des endpoints API

À exécuter sur le VPS (ou depuis une machine qui a accès au serveur). Si Nginx est en place, remplacer `localhost:8000` par ton domaine.

## Santé

```bash
curl -s http://localhost:8000/health | jq .
# Ou via le domaine :
curl -s https://srv1324425.hstgr.cloud/health | jq .
```

## Docs OpenAPI

- Swagger UI : https://DOMAINE/docs  
- ReDoc : https://DOMAINE/redoc  
- JSON : https://DOMAINE/openapi.json  

## Login (token)

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@mobilityhealth.com&password=TON_MOT_DE_PASSE" | jq .
```

Récupérer `access_token` dans la réponse, puis :

```bash
export TOKEN="eyJ..."
curl -s http://localhost:8000/api/v1/users/me -H "Authorization: Bearer $TOKEN" | jq .
```

## Endpoints utiles (avec token)

```bash
# Liste des rôles
curl -s http://localhost:8000/api/v1/roles -H "Authorization: Bearer $TOKEN" | jq .

# Destinations (pays)
curl -s http://localhost:8000/api/v1/destinations/countries -H "Authorization: Bearer $TOKEN" | jq .

# Produits d'assurance
curl -s http://localhost:8000/api/v1/produits-assurance -H "Authorization: Bearer $TOKEN" | jq .
```

## Résumé des commandes (sans jq)

```bash
curl -s http://localhost:8000/health
curl -s -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/x-www-form-urlencoded" -d "username=ADMIN_EMAIL&password=ADMIN_PASSWORD"
```
