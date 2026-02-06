# Schéma de la Base de Données

Ce document liste toutes les tables de la base de données avec leurs colonnes.

## Tables de Base (TimestampMixin)

Toutes les tables héritent de `TimestampMixin` qui ajoute automatiquement :
- `created_at` (DateTime, NOT NULL)
- `updated_at` (DateTime, NOT NULL)

---

## 1. users

**Description** : Utilisateurs du système

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| email | String | UNIQUE, INDEX, NOT NULL | Email de l'utilisateur |
| username | String | UNIQUE, INDEX, NOT NULL | Nom d'utilisateur |
| hashed_password | String | NOT NULL | Mot de passe hashé |
| full_name | String | NULLABLE | Nom complet |
| date_naissance | Date | NULLABLE | Date de naissance |
| telephone | String(20) | NULLABLE | Téléphone |
| sexe | String(10) | NULLABLE | Sexe (M, F, Autre) |
| is_active | Boolean | DEFAULT True | Compte actif |
| is_superuser | Boolean | DEFAULT False | Super utilisateur |
| role | Enum(Role) | NOT NULL, DEFAULT Role.USER | Rôle de l'utilisateur |
| role_id | Integer | FK(roles.id), INDEX, NULLABLE | ID du rôle personnalisé |
| hospital_id | Integer | FK(hospitals.id), INDEX, NULLABLE | ID de l'hôpital |
| created_by_id | Integer | FK(users.id), INDEX, NULLABLE | ID du créateur |

---

## 2. roles

**Description** : Rôles personnalisés dans le système

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| name | String(100) | UNIQUE, INDEX, NOT NULL | Nom du rôle |
| description | Text | NULLABLE | Description |
| permissions | Text | NULLABLE | Permissions (JSON string) |

---

## 3. hospitals

**Description** : Hôpitaux partenaires

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| nom | String(200) | INDEX, NOT NULL | Nom de l'hôpital |
| adresse | String(500) | NULLABLE | Adresse |
| ville | String(100) | NULLABLE | Ville |
| pays | String(100) | NULLABLE | Pays |
| code_postal | String(20) | NULLABLE | Code postal |
| telephone | String(50) | NULLABLE | Téléphone |
| email | String(255) | NULLABLE | Email |
| latitude | Numeric(10,8) | NOT NULL | Coordonnée GPS latitude |
| longitude | Numeric(11,8) | NOT NULL | Coordonnée GPS longitude |
| est_actif | Boolean | DEFAULT True, NOT NULL | Hôpital actif |
| specialites | Text | NULLABLE | Spécialités (JSON ou texte) |
| capacite_lits | Integer | NULLABLE | Capacité en lits |
| notes | Text | NULLABLE | Notes |
| medecin_referent_id | Integer | FK(users.id), INDEX, NULLABLE | ID du médecin référent |

---

## 4. assureurs

**Description** : Assureurs partenaires

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| nom | String(200) | UNIQUE, NOT NULL | Nom de l'assureur |
| pays | String(100) | NOT NULL | Pays |
| logo_url | String(500) | NULLABLE | URL du logo |
| adresse | String(255) | NULLABLE | Adresse |
| telephone | String(50) | NULLABLE | Téléphone |
| agent_comptable_id | Integer | FK(users.id), INDEX, NULLABLE | ID de l'agent comptable |

---

## 5. assureur_agents

**Description** : Liaison entre assureurs et agents (comptable, production, sinistre)

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| assureur_id | Integer | FK(assureurs.id), INDEX, NOT NULL | ID de l'assureur |
| user_id | Integer | FK(users.id), INDEX, NOT NULL, UNIQUE | ID de l'agent |
| type_agent | String(50) | NOT NULL | Type (comptable, production, sinistre) |

**Contraintes** : UNIQUE(user_id)

---

## 6. produits_assurance

**Description** : Produits d'assurance disponibles

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| code | String(50) | UNIQUE, INDEX, NOT NULL | Code du produit |
| nom | String(200) | NOT NULL | Nom du produit |
| description | Text | NULLABLE | Description |
| version | String(20) | NULLABLE | Version du produit |
| est_actif | Boolean | DEFAULT True, NOT NULL | Produit actif |
| assureur | String(200) | NULLABLE | Nom de l'assureur (legacy) |
| assureur_id | Integer | FK(assureurs.id), INDEX, NULLABLE | ID de l'assureur |
| image_url | String(500) | NULLABLE | URL de l'image |
| cout | Numeric(10,2) | NOT NULL | Coût de base |
| currency | String(10) | DEFAULT "XAF", NULLABLE | Devise |
| cle_repartition | Enum(CleRepartition) | NOT NULL, DEFAULT FIXE | Clé de répartition |
| zones_geographiques | JSON | NULLABLE | Zones géographiques couvertes |
| duree_min_jours | Integer | NULLABLE | Durée minimale (jours) |
| duree_max_jours | Integer | NULLABLE | Durée maximale (jours) |
| duree_validite_jours | Integer | NULLABLE | Durée de validité (jours) |
| reconduction_possible | Boolean | DEFAULT False, NOT NULL | Reconduction possible |
| couverture_multi_entrees | Boolean | DEFAULT False, NOT NULL | Multi-entrées |
| age_minimum | Integer | NULLABLE | Âge minimum |
| age_maximum | Integer | NULLABLE | Âge maximum |
| conditions_sante | Text | NULLABLE | Conditions de santé |
| categories_assures | JSON | NULLABLE | Catégories d'assurés |
| garanties | JSON | NULLABLE | Garanties incluses |
| exclusions_generales | JSON | NULLABLE | Exclusions générales |
| conditions | Text | NULLABLE | Conditions générales (legacy) |
| conditions_generales_pdf_url | String(500) | NULLABLE | URL PDF conditions |

---

## 7. historique_prix

**Description** : Historique des modifications de prix des produits

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| produit_assurance_id | Integer | FK(produits_assurance.id), INDEX, NOT NULL | ID du produit |
| ancien_prix | Numeric(10,2) | NULLABLE | Prix avant modification |
| nouveau_prix | Numeric(10,2) | NOT NULL | Nouveau prix |
| raison_modification | Text | NULLABLE | Raison du changement |
| modifie_par_user_id | Integer | FK(users.id), INDEX, NULLABLE | ID de l'utilisateur |

---

## 8. projets_voyage

**Description** : Projets de voyage des utilisateurs

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| user_id | Integer | FK(users.id), INDEX, NOT NULL | ID de l'utilisateur |
| titre | String(200) | NOT NULL | Titre du projet |
| description | Text | NULLABLE | Description |
| destination | String(200) | NOT NULL | Destination |
| date_depart | DateTime | NOT NULL | Date de départ |
| date_retour | DateTime | NULLABLE | Date de retour |
| nombre_participants | Integer | DEFAULT 1, NOT NULL | Nombre de participants |
| statut | Enum(StatutProjetVoyage) | DEFAULT EN_PLANIFICATION, NOT NULL | Statut |
| notes | Text | NULLABLE | Notes |
| budget_estime | Numeric(10,2) | NULLABLE | Budget estimé |
| questionnaire_type | Enum(QuestionnaireType) | DEFAULT LONG, NOT NULL | Type de questionnaire |

---

## 9. projet_voyage_documents

**Description** : Documents associés aux projets de voyage

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| projet_voyage_id | Integer | FK(projets_voyage.id), INDEX, NOT NULL | ID du projet |
| doc_type | String(50) | NOT NULL | Type de document |
| display_name | String(255) | NOT NULL | Nom d'affichage |
| bucket_name | String(63) | NOT NULL | Nom du bucket Minio |
| object_name | String(512) | NOT NULL | Nom de l'objet Minio |
| content_type | String(100) | NOT NULL | Type MIME |
| file_size | Integer | NOT NULL | Taille du fichier |
| uploaded_by | Integer | FK(users.id), NULLABLE | ID de l'uploader |
| uploaded_at | DateTime | NOT NULL | Date d'upload |
| minio_etag | String(64) | NULLABLE | ETag Minio |

---

## 10. contacts_proches

**Description** : Contacts proches des utilisateurs

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| user_id | Integer | FK(users.id), INDEX, NOT NULL | ID de l'utilisateur |
| nom | String(200) | NOT NULL | Nom |
| prenom | String(200) | NOT NULL | Prénom |
| telephone | String(20) | NOT NULL | Téléphone |
| email | String(255) | NULLABLE | Email |
| relation | String(100) | NULLABLE | Relation (famille, ami, etc.) |
| est_contact_urgence | Boolean | DEFAULT False, NOT NULL | Contact d'urgence |
| adresse | String(500) | NULLABLE | Adresse |
| pays | String(100) | NULLABLE | Pays |

---

## 11. souscriptions

**Description** : Souscriptions d'assurance

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| user_id | Integer | FK(users.id), INDEX, NOT NULL | ID de l'utilisateur |
| produit_assurance_id | Integer | FK(produits_assurance.id), INDEX, NOT NULL | ID du produit |
| projet_voyage_id | Integer | FK(projets_voyage.id), INDEX, NULLABLE | ID du projet voyage |
| numero_souscription | String(100) | UNIQUE, INDEX, NOT NULL | Numéro de souscription |
| prix_applique | Numeric(10,2) | NOT NULL | Prix final appliqué |
| date_debut | DateTime | NOT NULL | Date de début |
| date_fin | DateTime | NULLABLE | Date de fin |
| statut | Enum(StatutSouscription) | DEFAULT EN_ATTENTE, NOT NULL | Statut |
| notes | Text | NULLABLE | Notes |
| validation_medicale | String(20) | INDEX, NULLABLE | Validation médicale (pending, approved, rejected) |
| validation_medicale_par | Integer | FK(users.id), NULLABLE | ID du validateur médical |
| validation_medicale_date | DateTime | NULLABLE | Date validation médicale |
| validation_medicale_notes | Text | NULLABLE | Notes validation médicale |
| validation_technique | String(20) | INDEX, NULLABLE | Validation technique |
| validation_technique_par | Integer | FK(users.id), NULLABLE | ID du validateur technique |
| validation_technique_date | DateTime | NULLABLE | Date validation technique |
| validation_technique_notes | Text | NULLABLE | Notes validation technique |
| validation_finale | String(20) | INDEX, NULLABLE | Validation finale |
| validation_finale_par | Integer | FK(users.id), NULLABLE | ID du validateur final |
| validation_finale_date | DateTime | NULLABLE | Date validation finale |
| validation_finale_notes | Text | NULLABLE | Notes validation finale |
| demande_resiliation | String(20) | INDEX, NULLABLE | Demande de résiliation |
| demande_resiliation_date | DateTime | NULLABLE | Date demande résiliation |
| demande_resiliation_notes | Text | NULLABLE | Notes résiliation |
| demande_resiliation_par_agent | Integer | FK(users.id), NULLABLE | ID de l'agent |
| demande_resiliation_date_traitement | DateTime | NULLABLE | Date traitement résiliation |

---

## 12. questionnaires

**Description** : Questionnaires (court et long) remplis par les utilisateurs

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| souscription_id | Integer | FK(souscriptions.id), INDEX, NOT NULL | ID de la souscription |
| type_questionnaire | String(20) | INDEX, NOT NULL | Type (short ou long) |
| version | Integer | DEFAULT 1, NOT NULL | Version du questionnaire |
| reponses | JSON | NOT NULL | Réponses en JSON |
| statut | String(20) | DEFAULT "en_attente", NOT NULL | Statut (en_attente, complete, archive) |
| notes | Text | NULLABLE | Notes |

---

## 13. paiements

**Description** : Paiements des souscriptions

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| souscription_id | Integer | FK(souscriptions.id), INDEX, NOT NULL | ID de la souscription |
| user_id | Integer | FK(users.id), INDEX, NOT NULL | ID de l'utilisateur |
| montant | Numeric(10,2) | NOT NULL | Montant |
| type_paiement | Enum(TypePaiement) | NOT NULL | Type de paiement |
| statut | Enum(StatutPaiement) | DEFAULT EN_ATTENTE, NOT NULL | Statut |
| date_paiement | DateTime | NULLABLE | Date de paiement |
| reference_transaction | String(200) | UNIQUE, INDEX, NULLABLE | Référence transaction |
| reference_externe | String(200) | NULLABLE | Référence système externe |
| notes | Text | NULLABLE | Notes |
| montant_rembourse | Numeric(10,2) | NULLABLE | Montant remboursé (si partiel) |

---

## 14. attestations

**Description** : Attestations (provisoires et définitives)

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| souscription_id | Integer | FK(souscriptions.id), INDEX, NOT NULL | ID de la souscription |
| paiement_id | Integer | FK(paiements.id), INDEX, NULLABLE | ID du paiement |
| type_attestation | String(20) | INDEX, NOT NULL | Type (provisoire ou definitive) |
| numero_attestation | String(100) | UNIQUE, INDEX, NOT NULL | Numéro d'attestation |
| chemin_fichier_minio | String(500) | NOT NULL | Chemin dans Minio |
| bucket_minio | String(100) | DEFAULT "attestations", NOT NULL | Bucket Minio |
| url_signee | Text | NULLABLE | URL signée temporaire |
| date_expiration_url | DateTime | NULLABLE | Date expiration URL |
| carte_numerique_path | String(500) | NULLABLE | Chemin carte numérique |
| carte_numerique_bucket | String(100) | NULLABLE | Bucket carte numérique |
| carte_numerique_url | Text | NULLABLE | URL carte numérique |
| carte_numerique_expires_at | DateTime | NULLABLE | Expiration carte numérique |
| est_valide | Boolean | DEFAULT True, NOT NULL | Attestation valide |
| notes | Text | NULLABLE | Notes |

---

## 15. validations_attestation

**Description** : Validations d'attestation (médecin, technique, production)

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| attestation_id | Integer | FK(attestations.id), INDEX, NOT NULL | ID de l'attestation |
| type_validation | String(20) | INDEX, NOT NULL | Type (medecin, technique, production) |
| valide_par_user_id | Integer | FK(users.id), INDEX, NULLABLE | ID du validateur |
| est_valide | Boolean | DEFAULT False, NOT NULL | Validation effectuée |
| date_validation | DateTime | NULLABLE | Date de validation |
| commentaires | Text | NULLABLE | Commentaires |

---

## 16. alertes

**Description** : Alertes SOS

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| user_id | Integer | FK(users.id), INDEX, NOT NULL | ID de l'utilisateur |
| souscription_id | Integer | FK(souscriptions.id), INDEX, NULLABLE | ID de la souscription |
| numero_alerte | String(100) | UNIQUE, INDEX, NOT NULL | Numéro d'alerte |
| latitude | Numeric(10,8) | NOT NULL | Coordonnée GPS latitude |
| longitude | Numeric(11,8) | NOT NULL | Coordonnée GPS longitude |
| adresse | String(500) | NULLABLE | Adresse textuelle |
| description | Text | NULLABLE | Description de l'urgence |
| statut | String(20) | DEFAULT "en_attente", INDEX, NOT NULL | Statut (en_attente, en_cours, resolue, annulee) |
| priorite | String(20) | DEFAULT "normale", NOT NULL | Priorité (faible, normale, elevee, critique) |

---

## 17. sinistres

**Description** : Sinistres déclarés

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| alerte_id | Integer | FK(alertes.id), INDEX, NOT NULL | ID de l'alerte |
| souscription_id | Integer | FK(souscriptions.id), INDEX, NULLABLE | ID de la souscription |
| hospital_id | Integer | FK(hospitals.id), INDEX, NULLABLE | ID de l'hôpital |
| numero_sinistre | String(100) | UNIQUE, INDEX, NULLABLE | Numéro de sinistre |
| description | Text | NULLABLE | Description |
| statut | String(20) | DEFAULT "en_cours", INDEX, NOT NULL | Statut (en_cours, resolu, annule) |
| agent_sinistre_id | Integer | FK(users.id), INDEX, NULLABLE | ID de l'agent sinistre |
| medecin_referent_id | Integer | FK(users.id), INDEX, NULLABLE | ID du médecin référent |
| notes | Text | NULLABLE | Notes |

---

## 18. sinistre_process_steps

**Description** : Étapes du processus de traitement des sinistres

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| sinistre_id | Integer | FK(sinistres.id), INDEX, NOT NULL | ID du sinistre |
| step_key | String(64) | INDEX, NOT NULL | Clé de l'étape |
| titre | String(255) | NOT NULL | Titre de l'étape |
| description | Text | NULLABLE | Description |
| ordre | Integer | NOT NULL | Ordre d'exécution |
| statut | String(20) | DEFAULT PENDING, INDEX, NOT NULL | Statut de l'étape |
| completed_at | DateTime | NULLABLE | Date de complétion |
| actor_id | Integer | FK(users.id), INDEX, NULLABLE | ID de l'acteur |
| details | JSON | NULLABLE | Détails en JSON |

---

## 19. hospital_stays

**Description** : Séjours hospitaliers déclenchés suite à un sinistre

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| sinistre_id | Integer | FK(sinistres.id), UNIQUE, NOT NULL | ID du sinistre |
| hospital_id | Integer | FK(hospitals.id), INDEX, NOT NULL | ID de l'hôpital |
| patient_id | Integer | FK(users.id), NULLABLE | ID du patient |
| assigned_doctor_id | Integer | FK(users.id), NULLABLE | ID du médecin assigné |
| created_by_id | Integer | FK(users.id), NULLABLE | ID du créateur |
| status | String(20) | DEFAULT "in_progress", INDEX, NOT NULL | Statut du séjour |
| report_status | String(30) | DEFAULT "draft", INDEX, NOT NULL | Statut du rapport |
| started_at | DateTime | NULLABLE | Date de début |
| ended_at | DateTime | NULLABLE | Date de fin |
| orientation_notes | Text | NULLABLE | Notes d'orientation |
| report_motif_consultation | Text | NULLABLE | Motif de consultation |
| report_motif_hospitalisation | Text | NULLABLE | Motif d'hospitalisation |
| report_duree_sejour_heures | Integer | NULLABLE | Durée du séjour (heures) |
| report_actes | JSON | NULLABLE | Actes médicaux |
| report_examens | JSON | NULLABLE | Examens effectués |
| report_resume | Text | NULLABLE | Résumé |
| report_observations | Text | NULLABLE | Observations |
| report_submitted_at | DateTime | NULLABLE | Date de soumission du rapport |
| report_submitted_by | Integer | FK(users.id), NULLABLE | ID du soumetteur |
| validated_by_id | Integer | FK(users.id), NULLABLE | ID du validateur |
| validated_at | DateTime | NULLABLE | Date de validation |
| validation_notes | Text | NULLABLE | Notes de validation |

---

## 20. hospital_act_tarifs

**Description** : Tarification personnalisée des actes médicaux par hôpital

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| hospital_id | Integer | FK(hospitals.id), INDEX, NOT NULL | ID de l'hôpital |
| code | String(50) | INDEX, NULLABLE | Code de l'acte |
| nom | String(200) | NOT NULL | Nom de l'acte |
| description | Text | NULLABLE | Description |
| montant | Numeric(10,2) | NOT NULL | Montant |

---

## 21. hospital_exam_tarifs

**Description** : Tarification personnalisée des examens par hôpital

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| hospital_id | Integer | FK(hospitals.id), INDEX, NOT NULL | ID de l'hôpital |
| nom | String(200) | NOT NULL | Nom de l'examen |
| montant | Numeric(10,2) | NOT NULL | Montant |

---

## 22. prestations

**Description** : Prestations médicales d'un hôpital

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| hospital_id | Integer | FK(hospitals.id), INDEX, NOT NULL | ID de l'hôpital |
| sinistre_id | Integer | FK(sinistres.id), INDEX, NULLABLE | ID du sinistre |
| user_id | Integer | FK(users.id), INDEX, NULLABLE | ID de l'utilisateur |
| code_prestation | String(50) | INDEX, NOT NULL | Code de la prestation |
| libelle | String(200) | NOT NULL | Libellé |
| description | Text | NULLABLE | Description |
| montant_unitaire | Numeric(10,2) | NOT NULL | Montant unitaire |
| quantite | Integer | DEFAULT 1, NOT NULL | Quantité |
| montant_total | Numeric(10,2) | NOT NULL | Montant total |
| date_prestation | DateTime | NOT NULL | Date de la prestation |
| statut | String(20) | DEFAULT "pending", INDEX, NOT NULL | Statut (pending, validated, invoiced) |

---

## 23. invoices

**Description** : Factures basées sur les prestations

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| hospital_id | Integer | FK(hospitals.id), INDEX, NOT NULL | ID de l'hôpital |
| hospital_stay_id | Integer | FK(hospital_stays.id), UNIQUE, INDEX, NULLABLE | ID du séjour |
| numero_facture | String(100) | UNIQUE, INDEX, NOT NULL | Numéro de facture |
| montant_ht | Numeric(12,2) | NOT NULL | Montant HT |
| montant_tva | Numeric(12,2) | DEFAULT 0, NOT NULL | Montant TVA |
| montant_ttc | Numeric(12,2) | NOT NULL | Montant TTC |
| date_facture | DateTime | NOT NULL | Date de facture |
| date_echeance | DateTime | NULLABLE | Date d'échéance |
| statut | String(30) | DEFAULT "draft", INDEX, NOT NULL | Statut |
| validation_medicale | String(20) | INDEX, NULLABLE | Validation médicale |
| validation_medicale_par | Integer | FK(users.id), NULLABLE | ID validateur médical |
| validation_medicale_date | DateTime | NULLABLE | Date validation médicale |
| validation_medicale_notes | Text | NULLABLE | Notes validation médicale |
| validation_sinistre | String(20) | INDEX, NULLABLE | Validation sinistre |
| validation_sinistre_par | Integer | FK(users.id), NULLABLE | ID validateur sinistre |
| validation_sinistre_date | DateTime | NULLABLE | Date validation sinistre |
| validation_sinistre_notes | Text | NULLABLE | Notes validation sinistre |
| validation_compta | String(20) | INDEX, NULLABLE | Validation comptable |
| validation_compta_par | Integer | FK(users.id), NULLABLE | ID validateur comptable |
| validation_compta_date | DateTime | NULLABLE | Date validation comptable |
| validation_compta_notes | Text | NULLABLE | Notes validation comptable |
| notes | Text | NULLABLE | Notes |

---

## 24. invoice_items

**Description** : Lignes de facture (basées sur les prestations)

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| invoice_id | Integer | FK(invoices.id), INDEX, NOT NULL | ID de la facture |
| prestation_id | Integer | FK(prestations.id), INDEX, NULLABLE | ID de la prestation |
| libelle | String(200) | NOT NULL | Libellé |
| quantite | Integer | DEFAULT 1, NOT NULL | Quantité |
| prix_unitaire | Numeric(10,2) | NOT NULL | Prix unitaire |
| montant_ht | Numeric(10,2) | NOT NULL | Montant HT |
| taux_tva | Numeric(5,2) | DEFAULT 0, NOT NULL | Taux TVA |
| montant_ttc | Numeric(10,2) | NOT NULL | Montant TTC |

---

## 25. invoice_history

**Description** : Historique des modifications de factures

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| invoice_id | Integer | FK(invoices.id), INDEX, NOT NULL | ID de la facture |
| action | String(50) | NOT NULL | Action effectuée |
| previous_status | String(30) | NULLABLE | Statut précédent |
| new_status | String(30) | NULLABLE | Nouveau statut |
| previous_stage | String(30) | NULLABLE | Étape précédente |
| new_stage | String(30) | NULLABLE | Nouvelle étape |
| actor_id | Integer | FK(users.id), INDEX, NULLABLE | ID de l'acteur |
| notes | Text | NULLABLE | Notes |

---

## 26. rapports

**Description** : Rapports médicaux signés

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| hospital_id | Integer | FK(hospitals.id), INDEX, NOT NULL | ID de l'hôpital |
| sinistre_id | Integer | FK(sinistres.id), INDEX, NULLABLE | ID du sinistre |
| user_id | Integer | FK(users.id), INDEX, NULLABLE | ID de l'utilisateur |
| titre | String(200) | NOT NULL | Titre du rapport |
| type_rapport | String(50) | NOT NULL | Type (medical, technique, etc.) |
| contenu | Text | NULLABLE | Contenu textuel |
| fichier_path | String(500) | NULLABLE | Chemin vers le fichier Minio |
| fichier_nom | String(255) | NULLABLE | Nom original du fichier |
| fichier_taille | Integer | NULLABLE | Taille en bytes |
| fichier_type | String(100) | NULLABLE | Type MIME |
| est_signe | Boolean | DEFAULT False, NOT NULL | Rapport signé |
| signe_par | Integer | FK(users.id), NULLABLE | ID du signataire |
| date_signature | DateTime | NULLABLE | Date de signature |
| signature_digitale | Text | NULLABLE | Hash ou signature digitale |
| statut | String(20) | DEFAULT "draft", INDEX, NOT NULL | Statut (draft, signed, validated) |

---

## 27. notifications

**Description** : Notifications utilisateur

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| user_id | Integer | FK(users.id), INDEX, NOT NULL | ID de l'utilisateur |
| type_notification | String(50) | NOT NULL | Type de notification |
| titre | String(200) | NOT NULL | Titre |
| message | Text | NOT NULL | Message |
| is_read | Boolean | DEFAULT False, INDEX, NOT NULL | Notification lue |
| lien_relation_id | Integer | NULLABLE | ID lié |
| lien_relation_type | String(50) | NULLABLE | Type de relation |

---

## 28. audit_logs

**Description** : Logs d'audit des actions utilisateurs

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| timestamp | DateTime | INDEX, NOT NULL | Timestamp de l'action |
| method | String | NOT NULL | Méthode HTTP |
| path | String | NOT NULL | Chemin de la requête |
| query_params | Text | NULLABLE | Paramètres de requête |
| user_id | Integer | FK(users.id), INDEX, NULLABLE | ID de l'utilisateur |
| user_role | String | NULLABLE | Rôle de l'utilisateur |
| client_ip | String | NULLABLE | Adresse IP du client |
| user_agent | Text | NULLABLE | User agent |
| status_code | Integer | NOT NULL | Code de statut HTTP |
| request_body | Text | NULLABLE | Corps de la requête |
| response_body | Text | NULLABLE | Corps de la réponse |
| duration_ms | Integer | NULLABLE | Durée en millisecondes |

---

## 29. finance_accounts

**Description** : Comptes financiers

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| account_number | String(50) | UNIQUE, INDEX, NOT NULL | Numéro de compte |
| account_name | String(200) | NOT NULL | Nom du compte |
| account_type | String(50) | NOT NULL | Type (client, provider, internal, etc.) |
| balance | Numeric(12,2) | DEFAULT 0, NOT NULL | Solde |
| currency | String(3) | DEFAULT "EUR", NOT NULL | Devise |
| is_active | Boolean | DEFAULT True, NOT NULL | Compte actif |
| owner_id | Integer | FK(users.id), INDEX, NULLABLE | ID du propriétaire |

---

## 30. finance_movements

**Description** : Mouvements financiers (journal)

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| account_id | Integer | FK(finance_accounts.id), INDEX, NOT NULL | ID du compte |
| movement_type | String(50) | INDEX, NOT NULL | Type de mouvement |
| amount | Numeric(12,2) | NOT NULL | Montant |
| currency | String(3) | DEFAULT "EUR", NOT NULL | Devise |
| description | Text | NULLABLE | Description |
| reference | String(200) | INDEX, NULLABLE | Référence unique (anti-doublon) |
| reference_type | String(50) | NULLABLE | Type de référence (payment_id, etc.) |
| related_id | Integer | INDEX, NULLABLE | ID de l'entité liée |

---

## 31. finance_repartitions

**Description** : Répartitions financières

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| souscription_id | Integer | FK(souscriptions.id), INDEX, NOT NULL | ID de la souscription |
| paiement_id | Integer | FK(paiements.id), INDEX, NOT NULL | ID du paiement |
| produit_assurance_id | Integer | FK(produits_assurance.id), INDEX, NOT NULL | ID du produit |
| montant_total | Numeric(12,2) | NOT NULL | Montant total |
| cle_repartition | String(50) | NOT NULL | Clé de répartition |
| repartition_details | JSON | NULLABLE | Détails de la répartition |
| montant_par_personne | Numeric(12,2) | NULLABLE | Montant par personne |
| montant_par_groupe | Numeric(12,2) | NULLABLE | Montant par groupe |
| montant_par_duree | Numeric(12,2) | NULLABLE | Montant par durée |
| montant_par_destination | Numeric(12,2) | NULLABLE | Montant par destination |
| montant_fixe | Numeric(12,2) | NULLABLE | Montant fixe |
| notes | Text | NULLABLE | Notes |

---

## 32. finance_refunds

**Description** : Remboursements

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| paiement_id | Integer | FK(paiements.id), INDEX, NOT NULL | ID du paiement |
| souscription_id | Integer | FK(souscriptions.id), INDEX, NOT NULL | ID de la souscription |
| account_id | Integer | FK(finance_accounts.id), INDEX, NOT NULL | ID du compte |
| montant | Numeric(12,2) | NOT NULL | Montant |
| currency | String(3) | DEFAULT "EUR", NOT NULL | Devise |
| statut | String(20) | DEFAULT "pending", INDEX, NOT NULL | Statut |
| raison | Text | NOT NULL | Raison du remboursement |
| reference_remboursement | String(200) | UNIQUE, INDEX, NULLABLE | Référence de remboursement |
| date_remboursement | DateTime | NULLABLE | Date de remboursement |
| processed_by | Integer | FK(users.id), NULLABLE | ID du processeur |
| notes | Text | NULLABLE | Notes |

---

## 33. transaction_logs

**Description** : Logs des transactions de paiement

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| payment_id | Integer | FK(paiements.id), INDEX, NOT NULL | ID du paiement |
| user_id | Integer | FK(users.id), INDEX, NULLABLE | ID de l'utilisateur |
| action | String(100) | INDEX, NOT NULL | Action (payment_initiated, etc.) |
| details | JSON | NULLABLE | Détails en JSON |
| ip_address | String(45) | NULLABLE | Adresse IP |
| user_agent | Text | NULLABLE | User agent |

---

## 34. destination_countries

**Description** : Pays de destination pris en charge

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| code | String(10) | UNIQUE, INDEX, NOT NULL | Code ISO ou personnalisé |
| nom | String(200) | INDEX, NOT NULL | Nom du pays |
| est_actif | Boolean | DEFAULT True, NOT NULL | Pays actif |
| ordre_affichage | Integer | DEFAULT 0, NOT NULL | Ordre d'affichage |
| notes | String(500) | NULLABLE | Notes |

---

## 35. destination_cities

**Description** : Villes de destination associées aux pays

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| pays_id | Integer | FK(destination_countries.id), INDEX, NOT NULL | ID du pays |
| nom | String(200) | INDEX, NOT NULL | Nom de la ville |
| est_actif | Boolean | DEFAULT True, NOT NULL | Ville active |
| ordre_affichage | Integer | DEFAULT 0, NOT NULL | Ordre d'affichage |
| notes | String(500) | NULLABLE | Notes |

---

## 36. ia_analyses

**Description** : Analyses IA des demandes de souscription

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| souscription_id | Integer | FK(souscriptions.id), INDEX, NULLABLE | ID de la souscription |
| questionnaire_id | Integer | FK(questionnaires.id), INDEX, NULLABLE | ID du questionnaire |
| demande_id | String(100) | UNIQUE, INDEX, NOT NULL | ID de la demande |
| client_nom | String(200) | INDEX, NOT NULL | Nom du client |
| client_prenom | String(200) | INDEX, NOT NULL | Prénom du client |
| client_pays | String(100) | INDEX, NULLABLE | Pays du client |
| client_email | String(255) | INDEX, NULLABLE | Email du client |
| probabilite_acceptation | Numeric(5,3) | NOT NULL | Probabilité d'acceptation (0.000-1.000) |
| probabilite_fraude | Numeric(5,3) | NOT NULL | Probabilité de fraude |
| probabilite_confiance_assureur | Numeric(5,3) | NOT NULL | Probabilité de confiance assureur |
| score_coherence | Numeric(5,2) | NOT NULL | Score de cohérence (0.00-100.00) |
| score_risque | Numeric(5,3) | NOT NULL | Score de risque |
| score_confiance | Numeric(5,2) | NOT NULL | Score de confiance |
| avis | String(50) | INDEX, NOT NULL | Avis (FAVORABLE, RÉSERVÉ, DÉFAVORABLE, REJET) |
| niveau_risque | String(30) | NOT NULL | Niveau de risque |
| niveau_fraude | String(30) | NOT NULL | Niveau de fraude |
| niveau_confiance_assureur | String(30) | NOT NULL | Niveau de confiance assureur |
| facteurs_risque | JSON | NULLABLE | Liste des facteurs de risque |
| signaux_fraude | JSON | NULLABLE | Liste des signaux de fraude |
| incoherences | JSON | NULLABLE | Liste des incohérences |
| infos_personnelles | JSON | NULLABLE | Données personnelles extraites |
| infos_sante | JSON | NULLABLE | Questionnaire médical complet |
| infos_voyage | JSON | NULLABLE | Informations de voyage |
| resultat_complet | JSON | NULLABLE | Résultat complet de l'analyse |
| date_analyse | DateTime | INDEX, NOT NULL | Date de l'analyse |
| confiance_ocr | Numeric(5,2) | NULLABLE | Confiance moyenne OCR |
| nb_documents_analyses | Integer | DEFAULT 0, NOT NULL | Nombre de documents analysés |
| commentaire | Text | NULLABLE | Commentaire |
| message_ia | Text | NULLABLE | Message IA |

**Index** :
- idx_ia_analyses_avis_scores (avis, probabilite_acceptation, probabilite_fraude)
- idx_ia_analyses_date_avis (date_analyse, avis)
- idx_ia_analyses_client (client_nom, client_prenom)

---

## 37. ia_analysis_assureurs

**Description** : Liaison entre analyses IA et assureurs concernés

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| analyse_id | Integer | FK(ia_analyses.id), INDEX, NOT NULL | ID de l'analyse |
| assureur_id | Integer | FK(assureurs.id), INDEX, NOT NULL | ID de l'assureur |
| notifie | String(20) | DEFAULT "pending", INDEX, NOT NULL | Statut notification (pending, sent, failed) |
| date_notification | DateTime | NULLABLE | Date de notification |
| methode_notification | String(50) | NULLABLE | Méthode (email, webhook, api) |

**Index** :
- idx_ia_analysis_assureur_unique (analyse_id, assureur_id) UNIQUE

---

## 38. ia_analysis_documents

**Description** : Détails d'un document analysé dans une analyse IA

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| analyse_id | Integer | FK(ia_analyses.id), INDEX, NOT NULL | ID de l'analyse |
| nom_fichier | String(255) | NOT NULL | Nom du fichier |
| type_document | String(100) | NULLABLE | Type (Passeport, CNI, Questionnaire, etc.) |
| type_fichier | String(50) | NULLABLE | Type (PDF, PNG, JPG) |
| confiance_ocr | Numeric(5,2) | NULLABLE | Confiance OCR |
| texte_extrait | Text | NULLABLE | Texte extrait |
| est_expire | Boolean | DEFAULT False, NOT NULL | Document expiré |
| qualite_ok | Boolean | DEFAULT True, NOT NULL | Qualité OK |
| est_complet | Boolean | DEFAULT True, NOT NULL | Document complet |
| est_coherent | Boolean | DEFAULT True, NOT NULL | Document cohérent |
| message_expiration | Text | NULLABLE | Message expiration |
| message_qualite | Text | NULLABLE | Message qualité |
| message_completude | Text | NULLABLE | Message complétude |
| message_coherence | Text | NULLABLE | Message cohérence |
| resultat_document | JSON | NULLABLE | Résultat complet du document |

---

## 39. failed_tasks

**Description** : Tâches Celery échouées

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, INDEX | Identifiant unique |
| task_id | String(255) | UNIQUE, INDEX, NOT NULL | ID de la tâche Celery |
| task_name | String(255) | INDEX, NOT NULL | Nom de la tâche |
| task_args | JSON | NULLABLE | Arguments de la tâche |
| task_kwargs | JSON | NULLABLE | Arguments nommés de la tâche |
| error_message | Text | NOT NULL | Message d'erreur |
| error_traceback | Text | NULLABLE | Traceback de l'erreur |
| retry_count | Integer | DEFAULT 0, NOT NULL | Nombre de tentatives |
| max_retries | Integer | DEFAULT 3, NOT NULL | Nombre maximum de tentatives |
| is_resolved | Boolean | DEFAULT False, INDEX, NOT NULL | Tâche résolue |
| resolved_at | DateTime | NULLABLE | Date de résolution |
| queue_name | String(100) | INDEX, NULLABLE | Nom de la file d'attente |

---

## Résumé

**Total : 39 tables**

- **Utilisateurs et rôles** : users, roles, assureur_agents
- **Hôpitaux** : hospitals, hospital_stays, hospital_act_tarifs, hospital_exam_tarifs
- **Assureurs** : assureurs
- **Produits** : produits_assurance, historique_prix
- **Voyages** : projets_voyage, projet_voyage_documents, destination_countries, destination_cities
- **Souscriptions** : souscriptions, questionnaires, paiements, attestations, validations_attestation
- **Sinistres** : alertes, sinistres, sinistre_process_steps, prestations, rapports
- **Facturation** : invoices, invoice_items, invoice_history
- **Finance** : finance_accounts, finance_movements, finance_repartitions, finance_refunds, transaction_logs
- **IA** : ia_analyses, ia_analysis_assureurs, ia_analysis_documents
- **Autres** : contacts_proches, notifications, audit_logs, failed_tasks



