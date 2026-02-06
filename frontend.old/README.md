# Mobility Health Frontend

Application React pour la gestion des produits d'assurance.

## Installation

```bash
cd frontend
npm install
```

## Développement

```bash
npm run dev
```

L'application sera accessible sur http://localhost:3000

## Build

```bash
npm run build
```

## Tests

```bash
# Exécuter les tests
npm test

# Mode watch
npm run test:watch

# Avec couverture
npm run test:coverage
```

## Configuration

Créez un fichier `.env` à la racine du dossier frontend :

```
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

## Structure

- `src/pages/` - Pages de l'application
- `src/components/` - Composants réutilisables
- `src/api/` - Clients API
- `src/types/` - Types TypeScript
- `src/__tests__/` - Tests unitaires
