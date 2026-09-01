# Fonctionnalités de l'Application Mobile Mobility Health

Ce document liste toutes les fonctionnalités que l'application mobile doit implémenter pour les utilisateurs (rôle: `user`).

## 📱 Vue d'ensemble

L'application mobile est destinée aux **utilisateurs finaux** (assurés) qui souhaitent :
- Souscrire à des produits d'assurance voyage
- Gérer leurs souscriptions
- Accéder à leurs attestations
- Déclarer des sinistres (SOS)
- Remplir des questionnaires médicaux
- Consulter leurs documents et factures

---

## 🔐 1. AUTHENTIFICATION & COMPTE UTILISATEUR

### 1.1 Connexion / Inscription
- ✅ **Login** : Connexion avec username/password
- ✅ **Register** : Inscription avec email, username, password, nom complet
- ✅ **Logout** : Déconnexion sécurisée
- 🔄 **Refresh Token** : Rafraîchissement automatique des tokens
- 🔄 **Mot de passe oublié** :
  - Demande de réinitialisation par email
  - Vérification du code de réinitialisation
  - Réinitialisation du mot de passe

### 1.2 Profil Utilisateur
- 📋 **Voir mon profil** : Informations personnelles
- ✏️ **Modifier mon profil** : Mise à jour des informations
- 🔒 **Sécurité** : Changer le mot de passe

---

## 🛍️ 2. PRODUITS D'ASSURANCE

### 2.1 Consultation des Produits
- 📋 **Liste des produits** : Voir tous les produits d'assurance disponibles
- 🔍 **Filtres** : Filtrer par type, prix, caractéristiques
- 📄 **Détails d'un produit** :
  - Description complète
  - Caractéristiques
  - Prix
  - Durée de validité
  - Couvertures incluses

### 2.2 Sélection de Produit
- ➕ **Ajouter au panier** (si applicable)
- 🛒 **Comparer les produits** (fonctionnalité future)

---

## ✈️ 3. PROJETS DE VOYAGE

### 3.1 Gestion des Projets
- ➕ **Créer un projet de voyage** :
  - Destination
  - Date de départ
  - Date de retour
  - Nombre de participants
  - Notes
- 📋 **Liste de mes projets** : Voir tous mes projets de voyage
- 📄 **Détails d'un projet** : Informations complètes
- ✏️ **Modifier un projet** : Mise à jour des informations
- 🗑️ **Supprimer un projet** : Suppression (si pas de souscription associée)

### 3.2 Documents de Voyage
- 📎 **Ajouter des documents** :
  - Passeport
  - Carte d'identité
  - Titre de séjour
  - Réservation de voyage
  - Autres documents
- 📋 **Liste des documents** : Voir tous les documents d'un projet
- 📥 **Télécharger un document** : Téléchargement depuis Minio
- 🗑️ **Supprimer un document** : Suppression d'un document

---

## 📝 4. SOUSCRIPTIONS

### 4.1 Création de Souscription
- ➕ **Démarrer une souscription** :
  - Sélectionner un produit d'assurance
  - Optionnellement lier à un projet de voyage
  - Date de début (optionnelle)
  - Notes (optionnelles)
  - Calcul automatique du prix
- 💰 **Voir le prix** : Affichage du prix calculé
- 📄 **Numéro de souscription** : Génération automatique (ex: SUB-XXXXXXXX-YYYYMMDD)

### 4.2 Gestion des Souscriptions
- 📋 **Liste de mes souscriptions** :
  - Filtrer par statut (en_attente, active, expirée, annulée)
  - Trier par date
  - Recherche
- 📄 **Détails d'une souscription** :
  - Informations complètes
  - Statut
  - Dates (début, fin)
  - Prix
  - Produit associé
  - Projet de voyage associé (si applicable)
  - Historique des paiements
- 📊 **Statuts possibles** :
  - `en_attente` / `pending` : En attente de paiement
  - `active` : Souscription active
  - `expiree` / `expired` : Souscription expirée
  - `annulee` / `cancelled` : Souscription annulée

### 4.3 Carte Numérique (E-Card)
- 📱 **Voir ma carte numérique** : Pour les souscriptions actives
  - QR Code
  - Informations de la souscription
  - Informations de l'assuré
  - Numéro d'urgence
- 📥 **Télécharger la carte** : Export PDF/image

---

## 💳 5. PAIEMENTS

### 5.1 Paiement de Souscription
- 💰 **Payer une souscription** :
  - Sélectionner une souscription en attente
  - Choisir le mode de paiement
  - Confirmer le paiement
  - Voir le statut du paiement
- 📋 **Historique des paiements** :
  - Liste de tous mes paiements
  - Filtrer par statut (en_attente, valide, échoué, remboursé)
  - Détails d'un paiement
- 📄 **Détails d'un paiement** :
  - Montant
  - Date
  - Statut
  - Méthode de paiement
  - Référence de transaction

### 5.2 Statuts de Paiement
- `en_attente` : Paiement en cours
- `valide` : Paiement validé
- `echoue` : Paiement échoué
- `rembourse` : Paiement remboursé

---

## 📋 6. QUESTIONNAIRES MÉDICAUX

### 6.1 Questionnaire Court
- 📝 **Remplir le questionnaire court** :
  - Pour une souscription spécifique
  - Questions de base sur l'état de santé
  - Validation et soumission
- 📋 **Voir mes questionnaires courts** : Historique
- 📄 **Détails d'un questionnaire** : Réponses soumises

### 6.2 Questionnaire Long
- 📝 **Remplir le questionnaire long** :
  - Pour une souscription spécifique
  - Questions détaillées sur l'état de santé
  - Historique médical
  - Validation et soumission
- 📋 **Voir mes questionnaires longs** : Historique
- 📄 **Détails d'un questionnaire** : Réponses soumises

### 6.3 Gestion des Questionnaires
- 🔔 **Notifications de rappel** : Rappel pour remplir le questionnaire long (3 jours après le court)
- 📊 **Statut des questionnaires** :
  - `complete` : Questionnaire complété
  - `archive` : Ancienne version archivée
- 🔄 **Versions** : Gestion des versions multiples d'un questionnaire

---

## 📄 7. ATTESTATIONS

### 7.1 Consultation des Attestations
- 📋 **Liste de mes attestations** :
  - Filtrer par souscription
  - Filtrer par statut (en_attente, validee, rejetee)
  - Trier par date
- 📄 **Détails d'une attestation** :
  - Informations complètes
  - Statut de validation
  - Validations médicale et technique
  - URL de téléchargement PDF
- 📥 **Télécharger l'attestation** : Téléchargement du PDF
- 🔗 **Partager l'attestation** : Partage via URL de vérification

### 7.2 Statuts d'Attestation
- `en_attente` : En attente de validation
- `validee` : Attestation validée
- `rejetee` : Attestation rejetée

### 7.3 Vérification d'Attestation
- 🔍 **Vérifier une attestation** : Via URL de vérification publique
- 📱 **QR Code de vérification** : Scanner pour vérifier

---

## 🆘 8. ALERTES SOS / SINISTRES

### 8.1 Déclaration d'Alerte SOS
- 🚨 **Créer une alerte SOS** :
  - Pour une souscription active
  - Géolocalisation automatique (GPS)
  - Description de la situation
  - Photos (optionnelles)
  - Type d'urgence
- 📍 **Localisation** :
  - Coordonnées GPS
  - Adresse
  - Carte interactive
- 📸 **Ajouter des photos** : Prendre ou sélectionner des photos
- 📞 **Numéro d'urgence** : Appel direct depuis l'app

### 8.2 Suivi des Alertes
- 📋 **Liste de mes alertes** :
  - Filtrer par statut
  - Trier par date
  - Voir les alertes en cours
- 📄 **Détails d'une alerte** :
  - Informations complètes
  - Statut
  - Hôpital assigné
  - Distance à l'hôpital
  - Sinistre associé (si créé)
  - Historique des mises à jour
- 🔄 **Statuts d'alerte** :
  - `en_attente` : En attente de traitement
  - `en_cours` : En cours de traitement
  - `resolue` : Résolue
  - `annulee` : Annulée

### 8.3 Suivi des Sinistres
- 📋 **Liste de mes sinistres** :
  - Filtrer par statut
  - Trier par date
- 📄 **Détails d'un sinistre** :
  - Informations complètes
  - Statut du workflow
  - Étapes de validation
  - Hôpital assigné
  - Prestations
  - Séjours hospitaliers
  - Factures
- 🔄 **Workflow du sinistre** :
  - Vérification d'urgence
  - Validation médicale
  - Validation technique
  - Traitement
  - Clôture

### 8.4 Communication en Temps Réel
- 💬 **WebSocket** : Communication en temps réel avec le centre SOS
- 🔔 **Notifications push** : Mises à jour en temps réel
- 📱 **Chat** : Communication avec les opérateurs SOS (si implémenté)

---

## 🏥 9. HÔPITAUX

### 9.1 Recherche d'Hôpitaux
- 🔍 **Rechercher des hôpitaux** :
  - Par localisation (GPS)
  - Par nom
  - Par ville/pays
- 📍 **Carte des hôpitaux** : Voir les hôpitaux sur une carte
- 📋 **Liste des hôpitaux** : Liste avec distance
- 📄 **Détails d'un hôpital** :
  - Informations complètes
  - Coordonnées
  - Services disponibles
  - Tarifs
  - Contact
  - Distance depuis ma position

### 9.2 Hôpital Assigné
- 🏥 **Voir l'hôpital assigné** : Pour une alerte/sinistre en cours
- 📍 **Itinéraire** : Navigation vers l'hôpital
- 📞 **Contacter l'hôpital** : Appel direct

---

## 📧 10. NOTIFICATIONS

### 10.1 Notifications Push
- 🔔 **Recevoir des notifications** :
  - Nouvelles attestations
  - Mises à jour de sinistres
  - Rappels de questionnaires
  - Paiements
  - Alertes importantes
- 📋 **Liste des notifications** :
  - Filtrer par type
  - Marquer comme lues
  - Supprimer
- ⚙️ **Paramètres de notifications** : Activer/désactiver par type

### 10.2 Types de Notifications
- `questionnaire_completed` : Questionnaire complété
- `attestation_generated` : Attestation générée
- `attestation_validated` : Attestation validée
- `sinistre_updated` : Mise à jour de sinistre
- `payment_received` : Paiement reçu
- `subscription_active` : Souscription activée
- `alert_created` : Alerte créée

---

## 📊 11. TABLEAU DE BORD (DASHBOARD)

### 11.1 Vue d'Ensemble
- 📊 **Statistiques personnelles** :
  - Nombre de souscriptions actives
  - Nombre d'attestations
  - Nombre de sinistres en cours
  - Prochain paiement
- 📋 **Résumé récent** :
  - Dernières souscriptions
  - Dernières attestations
  - Derniers sinistres
  - Dernières notifications
- 🔔 **Notifications non lues** : Badge avec nombre

### 11.2 Accès Rapide
- 🚨 **Bouton SOS** : Accès rapide pour déclarer une urgence
- 📄 **Mes attestations** : Accès rapide
- 💳 **Mes paiements** : Accès rapide
- 📝 **Mes questionnaires** : Accès rapide

---

## 📁 12. DOCUMENTS

### 12.1 Gestion des Documents
- 📋 **Liste de mes documents** :
  - Documents de projets de voyage
  - Documents de sinistres
  - Factures
  - Autres documents
- 📥 **Télécharger un document** : Téléchargement depuis Minio
- 🔍 **Rechercher des documents** : Par nom, type, date
- 📂 **Organiser par catégorie** : Documents par type

---

## 🧾 13. FACTURES / INVOICES

### 13.1 Consultation des Factures
- 📋 **Liste de mes factures** :
  - Filtrer par statut
  - Trier par date
  - Recherche
- 📄 **Détails d'une facture** :
  - Informations complètes
  - Montant
  - Date
  - Statut
  - Souscription associée
- 📥 **Télécharger une facture** : Export PDF

---

## 🔍 14. RECHERCHE & FILTRES

### 14.1 Recherche Globale
- 🔍 **Recherche unifiée** : Rechercher dans tous les contenus
- 📋 **Filtres avancés** : Par date, statut, type
- 🔄 **Tri** : Par date, nom, statut

---

## ⚙️ 15. PARAMÈTRES

### 15.1 Paramètres de l'Application
- 🌐 **Langue** : Sélection de la langue (FR, EN, etc.)
- 🔔 **Notifications** : Paramètres de notifications
- 🔒 **Sécurité** :
  - Changer le mot de passe
  - Authentification à deux facteurs (si implémenté)
- 📱 **Préférences** :
  - Thème (clair/sombre)
  - Taille de police
- 📊 **Données** :
  - Exporter mes données
  - Supprimer mon compte

---

## 🗺️ 16. FONCTIONNALITÉS GÉOGRAPHIQUES

### 16.1 Géolocalisation
- 📍 **Position actuelle** : Utilisation du GPS
- 🗺️ **Carte interactive** :
  - Voir ma position
  - Voir les hôpitaux à proximité
  - Navigation vers un hôpital
- 🔍 **Recherche par localisation** : Trouver des services à proximité

---

## 📱 17. FONCTIONNALITÉS MOBILES SPÉCIFIQUES

### 17.1 Appareil Photo
- 📸 **Prendre des photos** : Pour les alertes SOS, documents
- 🖼️ **Sélectionner des photos** : Depuis la galerie

### 17.2 Appels Téléphoniques
- 📞 **Appel d'urgence** : Appel direct au numéro SOS
- 📞 **Appeler un hôpital** : Depuis les détails de l'hôpital

### 17.3 Partage
- 🔗 **Partager des attestations** : Via URL de vérification
- 📤 **Partager des documents** : Via différentes méthodes

### 17.4 Mode Hors Ligne
- 💾 **Cache local** : Stocker les données importantes
- 🔄 **Synchronisation** : Synchroniser quand la connexion revient

---

## 📊 18. STATISTIQUES & HISTORIQUE

### 18.1 Statistiques Personnelles
- 📈 **Mes statistiques** :
  - Nombre total de souscriptions
  - Nombre total de sinistres
  - Montant total payé
  - Durée moyenne des voyages
- 📅 **Historique** :
  - Historique des souscriptions
  - Historique des paiements
  - Historique des sinistres

---

## 🎯 PRIORITÉS DE DÉVELOPPEMENT

### Phase 1 - Essentiel (MVP)
1. ✅ Authentification (Login/Register/Logout)
2. 📋 Liste des produits
3. ➕ Créer une souscription
4. 📋 Liste de mes souscriptions
5. 💳 Paiement
6. 📄 Attestations
7. 🚨 Alerte SOS (création)
8. 📋 Liste de mes alertes

### Phase 2 - Important
9. 📝 Questionnaires (court et long)
10. ✈️ Projets de voyage
11. 🏥 Recherche d'hôpitaux
12. 📊 Dashboard utilisateur
13. 🔔 Notifications
14. 📁 Documents

### Phase 3 - Amélioration
15. 📊 Statistiques personnelles
16. 🔍 Recherche avancée
17. 💬 Communication temps réel (WebSocket)
18. 📱 Mode hors ligne
19. ⚙️ Paramètres avancés

---

## 🔗 ENDPOINTS API CORRESPONDANTS

### Authentification
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`

### Produits
- `GET /api/v1/products`
- `GET /api/v1/products/{id}`

### Souscriptions
- `POST /api/v1/subscriptions/start`
- `GET /api/v1/subscriptions`
- `GET /api/v1/subscriptions/{id}`
- `GET /api/v1/subscriptions/{id}/ecard`

### Paiements
- `POST /api/v1/payments`
- `GET /api/v1/payments`

### Questionnaires
- `POST /api/v1/subscriptions/{id}/questionnaire/short`
- `POST /api/v1/subscriptions/{id}/questionnaire/long`
- `GET /api/v1/questionnaires`

### Attestations
- `GET /api/v1/attestations`
- `GET /api/v1/attestations/{id}`
- `GET /api/v1/users/me/attestations`

### SOS / Sinistres
- `POST /api/v1/sos/alerts`
- `GET /api/v1/sos/alerts`
- `GET /api/v1/sos/alerts/{id}`
- `GET /api/v1/sos/sinistres`
- `GET /api/v1/sos/sinistres/{id}`

### Voyages
- `POST /api/v1/voyages`
- `GET /api/v1/voyages`
- `GET /api/v1/voyages/{id}`
- `PUT /api/v1/voyages/{id}`
- `DELETE /api/v1/voyages/{id}`
- `POST /api/v1/voyages/{id}/documents`
- `GET /api/v1/voyages/{id}/documents`

### Hôpitaux
- `GET /api/v1/hospitals`
- `GET /api/v1/hospitals/{id}`

### Notifications
- `GET /api/v1/notifications`
- `PUT /api/v1/notifications/{id}/read`

### Dashboard
- `GET /api/v1/dashboard` (pour utilisateur)

### Documents
- `GET /api/v1/documents`

### Factures
- `GET /api/v1/invoices`

---

## 📝 NOTES IMPORTANTES

1. **Rôle Utilisateur** : Toutes ces fonctionnalités sont pour le rôle `user`. Les fonctionnalités admin/back-office ne sont pas incluses.

2. **Sécurité** : Toutes les requêtes nécessitent un token d'authentification valide.

3. **Géolocalisation** : Les permissions GPS doivent être demandées pour les fonctionnalités SOS.

4. **Notifications Push** : Nécessite la configuration FCM (Firebase Cloud Messaging).

5. **Paiements** : L'intégration avec un système de paiement externe doit être implémentée.

6. **WebSocket** : Pour la communication temps réel avec le centre SOS.

---

## ✅ CHECKLIST DE DÉVELOPPEMENT

- [ ] Authentification complète
- [ ] Gestion des produits
- [ ] Gestion des projets de voyage
- [ ] Gestion des souscriptions
- [ ] Système de paiement
- [ ] Questionnaires médicaux
- [ ] Attestations
- [ ] Système SOS/Sinistres
- [ ] Recherche d'hôpitaux
- [ ] Notifications push
- [ ] Dashboard utilisateur
- [ ] Gestion des documents
- [ ] Factures
- [ ] Géolocalisation
- [ ] Mode hors ligne (optionnel)
- [ ] Tests unitaires
- [ ] Tests d'intégration
- [ ] Documentation utilisateur

---

**Dernière mise à jour** : Basé sur l'analyse du backend FastAPI

