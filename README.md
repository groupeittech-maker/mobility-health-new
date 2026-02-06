# Mobility Health - Backend API

## 📋 Description

Backend API pour la plateforme Mobility Health - Version FastAPI (v2.0)

## 🏗️ Architecture

- **Framework**: FastAPI (Python 3.11+)
- **Base de données**: SQLite (développement) / PostgreSQL (production)
- **ORM**: SQLAlchemy 2.0
- **Migrations**: Alembic
- **Authentification**: JWT (access + refresh tokens)
- **Cache/Tâches**: Redis + Celery
- **Stockage**: MinIO

## 🚀 Installation

### Prérequis

- Python 3.11+
- SQLite (développement) ou PostgreSQL (production)
- Redis (optionnel pour le développement)
- MinIO (optionnel pour le développement)

### Configuration

1. Cloner le dépôt :
```bash
git clone https://github.com/Mobility-Health/Mobility-Health-backend.git
cd Mobility-Health-backend
```

2. Installer les dépendances :
```bash
pip install -r requirements.txt
```

3. Configurer les variables d'environnement :
```bash
cp env.example .env
# Éditer .env avec vos configurations
```

4. Créer la base de données (SQLite par défaut) :
```bash
alembic upgrade head
```

5. Démarrer le serveur :
```bash
uvicorn app.main:app --reload
```

L'API sera accessible sur `http://localhost:8000`

## 📚 Documentation API

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🌿 Branches

- **Backend-fastAPI**: Version actuelle avec FastAPI (v2.0)
- **main/master**: Peut contenir l'ancienne version Django (v1.0)

## 🔧 Structure du projet

```
app/
├── api/           # Endpoints API
├── core/          # Configuration et utilitaires
├── models/        # Modèles SQLAlchemy
├── schemas/       # Schémas Pydantic
├── services/      # Services métier
├── middleware/    # Middlewares personnalisés
├── workers/       # Tâches Celery
└── tests/         # Tests unitaires
```

## 📝 Notes

- Le projet utilise SQLite par défaut pour le développement
- Pour passer à PostgreSQL, décommenter les lignes dans `app/core/config.py` et `app/core/database.py`
- Utiliser `alembic upgrade head` pour créer/mettre à jour les tables

## 📄 Licence

Propriétaire - Mobility Health

