# Récupération du code Flutter Mobility Health

## Situation

Dans ce dépôt, le dossier **mobile-app** ne contient **pas** l’ancien code Flutter complet (écran de connexion attendu, écrans métier, etc.). Il contient :

- **pubspec.yaml** et la config du projet
- **Documentation** (FONCTIONNALITES.md, guides, scripts)
- Un **écran de connexion minimal** ajouté pour faire tourner l’app et tester le backend

L’historique Git ne montre qu’un commit pour `mobile-app/` ; le code UI complet n’a jamais été versionné ici.

## Où retrouver votre code Flutter d’origine

1. **Autre dépôt Git**  
   Projet Flutter dans un autre repo (GitHub, GitLab, Bitbucket, etc.).

2. **Sauvegarde / autre PC**  
   Copie du projet sur disque externe, cloud (Drive, Dropbox), ou autre poste.

3. **Ancien clone**  
   Un autre dossier sur votre machine (recherche par nom : `mobility_health`, `MobilityHealth`, etc.).

4. **Équipe / prestataire**  
   Si l’app a été développée par quelqu’un d’autre, lui demander le code source ou un export.

## Si vous ne retrouvez pas l’ancien code

Une **nouvelle base** a été ajoutée dans ce dépôt, alignée sur **FONCTIONNALITES.md** et le backend :

- Écran de **connexion** (avec lien inscription / mot de passe oublié)
- **Inscription**
- Stockage du **token** (rester connecté)
- **Navigation principale** (accueil, souscriptions, attestations, SOS, profil)

Vous pouvez repartir de cette base et compléter écran par écran (produits, voyages, paiements, questionnaires, etc.) en vous aidant de FONCTIONNALITES.md et des endpoints du backend.

## Fichiers à conserver si vous récupérez l’ancien projet

Si vous retrouvez l’ancien code Flutter ailleurs :

- Garder ou recopier votre **`.env`** (ou recréer avec `API_BASE_URL=https://srv1324425.hstgr.cloud/api/v1`).
- Récupérer tout le dossier **lib/** (et éventuellement **assets/**) de l’ancien projet.
- Remplacer le contenu actuel de **lib/** par celui de l’ancien projet, en gardant la même racine `mobile-app` et en conservant **pubspec.yaml** / **android/** / **ios/** si besoin.

Ensuite : `flutter pub get` puis `flutter run`.
