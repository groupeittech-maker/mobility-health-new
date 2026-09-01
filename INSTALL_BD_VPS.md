# Installer la base de données sur le VPS

Sur le VPS, vous pouvez soit utiliser **PostgreSQL via Docker** (recommandé), soit **PostgreSQL installé directement** sur le serveur.

---

## Option 1 : Avec Docker (recommandé)

PostgreSQL, Redis et MinIO tournent dans des conteneurs. L’application utilise la base sans rien installer sur l’hôte.

### 1. Vérifier / installer Docker sur le VPS

Connecté en SSH (`ssh srv1324425`) :

```bash
# Vérifier si Docker est installé
docker --version
docker compose version
```

Si ce n’est pas installé (Debian/Ubuntu) :

```bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### 2. Aller dans le projet et démarrer les services

```bash
cd /opt/mobility-health-new
# ou le chemin où se trouve le projet, ex: cd /var/www/Mobility_Health/...
```

Créer un fichier `.env` à la racine du projet si besoin (copier depuis `env.example`) et définir au minimum :

```bash
# Base de données (utilisées par docker-compose pour le conteneur db)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=VOTRE_MOT_DE_PASSE_SECURISE
POSTGRES_DB=mobility_health

# URL pour l'API (dans le conteneur api, le service s'appelle "db")
DATABASE_URL=postgresql://postgres:VOTRE_MOT_DE_PASSE_SECURISE@db:5432/mobility_health
```

Puis lancer les conteneurs (dont PostgreSQL) :

```bash
sudo docker compose up -d
```

Cela crée et démarre la base **mobility_health** dans le conteneur `db`. Les données sont conservées dans le volume Docker `postgres_data`.

### 3. Créer les tables (migrations Alembic)

Une fois les conteneurs démarrés :

```bash
sudo docker compose exec api alembic upgrade head
```

Si une migration échoue (ex. table manquante), suivre les étapes de **INSTALL_VPS_MIGRATIONS.md** (scripts SQL de correction, etc.).

### 4. Vérifier

```bash
# Santé de l’API
curl http://localhost:8000/health

# Connexion à PostgreSQL dans le conteneur
sudo docker compose exec db psql -U postgres -d mobility_health -c "\dt"
```

---

## Option 2 : PostgreSQL installé sur le VPS (sans Docker)

Si vous ne voulez pas utiliser Docker pour la base, installez PostgreSQL directement sur le serveur.

### 1. Installer PostgreSQL (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

### 2. Créer l’utilisateur et la base

```bash
sudo -u postgres psql -c "CREATE USER mobility_health WITH PASSWORD 'VOTRE_MOT_DE_PASSE_SECURISE';"
sudo -u postgres psql -c "CREATE DATABASE mobility_health OWNER mobility_health;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE mobility_health TO mobility_health;"
```

(Remplacez `VOTRE_MOT_DE_PASSE_SECURISE` par un mot de passe fort.)

### 3. Autoriser les connexions (si l’app est sur le même serveur)

Par défaut, la connexion en `localhost` est possible. Vérifier dans `/etc/postgresql/15/main/pg_hba.conf` (le 15 peut être 14 ou 16 selon la version) qu’une ligne autorise les connexions en mot de passe, par exemple :

```
local   all             all                                     peer
host    all             all             127.0.0.1/32            scram-sha-256
```

Puis :

```bash
sudo systemctl reload postgresql
```

### 4. Configurer l’application

Dans le `.env` du projet sur le VPS :

```bash
DATABASE_URL=postgresql://mobility_health:VOTRE_MOT_DE_PASSE_SECURISE@localhost:5432/mobility_health
```

Si vous utilisez l’utilisateur `postgres` à la place :

```bash
DATABASE_URL=postgresql://postgres:VOTRE_MOT_DE_PASSE@localhost:5432/mobility_health
```

### 5. Lancer les migrations

Depuis le répertoire du projet, avec le venv activé :

```bash
cd /opt/mobility-health-new
source venv/bin/activate   # ou sur Ubuntu: . venv/bin/activate
alembic upgrade head
```

### 6. Vérifier

```bash
psql -U mobility_health -d mobility_health -h localhost -c "\dt"
# ou avec l’utilisateur postgres :
sudo -u postgres psql -d mobility_health -c "\dt"
```

---

## Résumé

| Méthode        | Commande principale              | Fichier de config      |
|----------------|-----------------------------------|------------------------|
| Docker         | `docker compose up -d`            | `.env` + docker-compose |
| PostgreSQL seul| `apt install postgresql` + create user/DB | `.env` (DATABASE_URL) |

Pour une installation type “tout en conteneurs”, utilisez **Option 1**. Pour un PostgreSQL dédié sur l’hôte, utilisez **Option 2**.
