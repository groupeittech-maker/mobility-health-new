# Mise à jour des migrations sur le VPS uniquement

En local les migrations passent déjà. Sur le VPS, `alembic upgrade head` échoue car la table `souscriptions` (et ses dépendances) n’existe pas au moment de la migration `ad587bb061e5`. Cette procédure corrige **uniquement sur le VPS**, sans modifier le code du dépôt.

## Prérequis

- Conteneurs Docker démarrés : `sudo docker compose up -d`

## Ordre obligatoire

1. **D'abord** : faire créer la table `users` (et les autres tables de base) par Alembic.
2. **Ensuite** : exécuter le script SQL qui crée `souscriptions` et les tables liées.
3. **Enfin** : relancer Alembic jusqu'à `head`.

## Étapes sur le VPS

1. **Aller dans le répertoire du projet** (adapter le chemin si besoin) :
   ```bash
   cd "/var/www/Mobility_Health/Mobility Health"
   ```

2. **Créer la table `users` et les tables de base** (obligatoire avant le script SQL) :
   ```bash
   sudo docker compose exec api alembic upgrade d103085117c7
   ```
   Cela crée notamment `users`, `audit_logs`, `paiements`, `transaction_logs`.

3. **Créer les tables manquantes** (à exécuter après que la table `users` existe) :
   ```bash
   cat scripts/vps_fix_tables_before_alembic.sql | sudo docker compose exec -T db psql -U postgres -d mobility_health
   ```
   Les messages du type "relation already exists" ou "already exists" peuvent être ignorés si les tables ont déjà été créées lors d’un essai précédent.

4. **Relancer les migrations Alembic jusqu'à la fin** :
   ```bash
   sudo docker compose exec api alembic upgrade head
   ```

5. **Vérifier l’API** :
   ```bash
   curl http://localhost:8000/health
   ```

## Si le fichier SQL n'est pas sur le VPS

Le script n'est présent qu'après un `git pull` (ou après l'avoir copié). Sinon, sur le VPS :

1. `mkdir -p scripts`
2. `nano scripts/vps_fix_tables_before_alembic.sql` puis coller tout le contenu du fichier `scripts/vps_fix_tables_before_alembic.sql` du dépôt local. Sauvegarder (Ctrl+O, Entrée, Ctrl+X).
3. `cat scripts/vps_fix_tables_before_alembic.sql | sudo docker compose exec -T db psql -U postgres -d mobility_health`

## Si Alembic échoue avec "relation \"hospitals\" does not exist"

Exécuter le script complémentaire puis relancer Alembic :
```bash
cat scripts/vps_fix_tables_hospitals.sql | sudo docker compose exec -T db psql -U postgres -d mobility_health
sudo docker compose exec api alembic upgrade head
```
(Si le fichier n'est pas sur le VPS : le créer avec le contenu de `scripts/vps_fix_tables_hospitals.sql` puis exécuter la commande `cat`.)

## Si Alembic échoue avec "relation \"sinistres\" does not exist"

Exécuter le script complémentaire puis relancer Alembic :
```bash
cat scripts/vps_fix_tables_sinistres.sql | sudo docker compose exec -T db psql -U postgres -d mobility_health
sudo docker compose exec api alembic upgrade head
```
(Si le fichier n'est pas sur le VPS : le créer avec le contenu de `scripts/vps_fix_tables_sinistres.sql`.)

## Si Alembic échoue avec "relation \"invoices\" does not exist"

Cette erreur apparaît lors de la migration **2c3b1a84b0e4** (Add validation metadata and invoice link to hospital stays). Les tables `invoices`, `invoice_items` et `prestations` ne sont créées par aucune migration ; il faut les créer manuellement.

**Prérequis** : `users`, `hospitals` et `sinistres` doivent exister (étape 3 déjà exécutée avec `vps_fix_tables_before_alembic.sql`).

Exécuter le script puis relancer Alembic :
```bash
cat scripts/vps_fix_tables_invoices.sql | sudo docker compose exec -T db psql -U postgres -d mobility_health
sudo docker compose exec api alembic upgrade head
```
(Si le fichier n'est pas sur le VPS : le créer avec le contenu de `scripts/vps_fix_tables_invoices.sql`.)

## Si Alembic échoue avec "column \"assureur_id\" of relation \"produits_assurance\" already exists"

La table `produits_assurance` a été créée par `vps_fix_tables_before_alembic.sql` avec la colonne `assureur_id`. La migration **b6c21f3b0c8d** tente de l’ajouter à nouveau. Il faut marquer cette révision comme déjà appliquée, puis continuer :

```bash
sudo docker compose exec api alembic stamp b6c21f3b0c8d
sudo docker compose exec api alembic upgrade head
```

## Si Alembic échoue avec "column \"questionnaire_type\" of relation \"projets_voyage\" already exists"

La table `projets_voyage` a été créée par `vps_fix_tables_before_alembic.sql` avec la colonne `questionnaire_type`. La migration **0d2e6a1b8c34** tente de l'ajouter et crée aussi la table `projet_voyage_documents`. Procédure :

1. **Créer la table manquante** (la migration ne sera pas exécutée, il faut créer `projet_voyage_documents` à la main) :
   ```bash
   cat scripts/vps_fix_tables_projet_documents.sql | sudo docker compose exec -T db psql -U postgres -d mobility_health
   ```

2. **Marquer la révision comme appliquée puis continuer** :
   ```bash
   sudo docker compose exec api alembic stamp 0d2e6a1b8c34
   sudo docker compose exec api alembic upgrade head
   ```

(Si le fichier n'est pas sur le VPS : créer `scripts/vps_fix_tables_projet_documents.sql` avec le contenu du dépôt.)

## Si Alembic échoue avec "relation \"destination_countries\" already exists"

Les tables `destination_countries` et `destination_cities` ont été créées par `vps_fix_tables_before_alembic.sql`. La migration **add_destinations** tente de les recréer. Marquer la révision comme déjà appliquée puis continuer :

```bash
sudo docker compose exec api alembic stamp add_destinations
sudo docker compose exec api alembic upgrade head
```

## En cas de problème

- Si le script SQL échoue sur `users` n’existe pas : exécuter d’abord `sudo docker compose exec api alembic upgrade d103085117c7` (s’arrêter juste avant la migration qui crée `questionnaires`), puis l’étape 2, puis l’étape 3.
- Base et utilisateur PostgreSQL : vérifier dans `.env` ou `docker-compose` que la base s’appelle bien `mobility_health` et l’utilisateur `postgres` (ou adapter la commande `psql` en conséquence).
