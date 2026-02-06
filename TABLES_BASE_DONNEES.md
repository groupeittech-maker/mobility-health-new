# Tables de la base de données Mobility Health

Document de référence des tables et de leur rôle. Utilisé pour le nettoyage de la base en conservant les configurations de base.

---

## Tables conservées (configurations de base)

| Table | Rôle |
|-------|------|
| **roles** | Rôles système (admin, user, doctor, hospital_admin, etc.). Requis pour les utilisateurs. |
| **assureurs** | Assureurs partenaires (nom, pays, logo, agent comptable). Configuration métier. |
| **produits_assurance** | Produits d'assurance (code, nom, coût, garanties, zones). Catalogue. |
| **hospitals** | Hôpitaux (nom, adresse, coordonnées, médecin référent). Configuration. |
| **hospital_act_tarifs** | Tarifs des actes par hôpital. Configuration. |
| **hospital_exam_tarifs** | Tarifs des examens par hôpital. Configuration. |
| **destination_countries** | Pays de destination pris en charge (code, nom). Référentiel. |
| **destination_cities** | Villes par pays de destination. Référentiel. |
| **users** (admin uniquement) | Utilisateur(s) avec rôle `admin` conservé(s). |

**Note :** Il n’existe pas de tables séparées « pays » ou « nationalité ». Les champs `pays_residence` et `nationalite` sont des chaînes dans la table **users**. Les pays de destination et villes sont dans **destination_countries** et **destination_cities**.

---

## Tables nettoyées (données métier / opérationnelles)

| Table | Rôle |
|-------|------|
| **users** (hors admin) | Utilisateurs (abonnés, médecins, réception, etc.). On supprime tout sauf les comptes admin. |
| **contacts_proches** | Contacts d’urgence des utilisateurs. |
| **projets_voyage** | Projets de voyage des utilisateurs. |
| **projet_voyage_documents** | Documents attachés aux projets de voyage. |
| **souscriptions** | Souscriptions aux produits d’assurance. |
| **paiements** | Paiements liés aux souscriptions. |
| **historique_prix** | Historique des prix des produits (on nettoie pour repartir à zéro). |
| **questionnaires** | Questionnaires (court, long, administratif, médical) liés aux souscriptions. |
| **attestations** | Attestations d’assurance générées. |
| **validations_attestation** | Validations (technique, production) des attestations. |
| **notifications** | Notifications utilisateurs. |
| **prestations** | Prestations médicales (hôpitaux). |
| **rapports** | Rapports médicaux. |
| **hospital_stays** | Séjours hospitaliers. |
| **invoices** | Factures (prestations / séjours). |
| **invoice_items** | Lignes de facture. |
| **invoice_history** | Historique des changements de statut des factures. |
| **sinistres** | Sinistres déclarés. |
| **sinistre_process_steps** | Étapes du workflow sinistre. |
| **alertes** | Alertes (ex. SOS). |
| **audit_logs** | Journaux d’audit. |
| **transaction_logs** | Journaux de transactions. |
| **failed_tasks** | Tâches Celery en échec. |
| **finance_accounts** | Comptes financiers. |
| **finance_movements** | Mouvements / écritures sur les comptes. |
| **finance_repartitions** | Répartitions (souscription, paiement, produit). |
| **finance_refunds** | Remboursements. |
| **ia_analyses** | Analyses IA des demandes de souscription. |
| **ia_analysis_assureurs** | Liaison analyse IA ↔ assureurs notifiés. |
| **ia_analysis_documents** | Détails des documents analysés par l’IA. |
| **assureur_agents** | Liaison assureur ↔ utilisateurs (agents). Nettoyé puis recréable par l’admin. |

---

## Ordre des dépendances (pour suppression)

Pour éviter les violations de clés étrangères, les suppressions sont faites des tables « enfants » vers les « parents » :

1. `invoice_history`, `invoice_items` → puis `invoices`
2. `validations_attestation` → puis `attestations`
3. `sinistre_process_steps` → puis `sinistres`
4. `hospital_stays`, `prestations`, `rapports`
5. `questionnaires`, `notifications`
6. `finance_refunds`, `finance_repartitions`, `finance_movements` → puis `finance_accounts`
7. `paiements`
8. `ia_analysis_documents`, `ia_analysis_assureurs` → puis `ia_analyses`
9. `historique_prix`
10. `projet_voyage_documents` → puis `souscriptions` → puis `projets_voyage`
11. `contacts_proches`
12. `audit_logs`, `transaction_logs`, `alertes`, `failed_tasks`
13. `assureur_agents`
14. Mise à NULL de `hospitals.medecin_referent_id` et `assureurs.agent_comptable_id` pour les utilisateurs non-admin
15. Suppression des **users** dont le rôle n’est pas `admin`

---

## Résumé

- **Conservé :** roles, assureurs, produits_assurance, hospitals, hospital_act_tarifs, hospital_exam_tarifs, destination_countries, destination_cities, et le(s) utilisateur(s) admin.
- **Nettoyé :** toutes les autres tables listées ci-dessus, et les utilisateurs non-admin.

Après nettoyage, la base permet de retester le logiciel « à neuf » tout en gardant les référentiels et l’accès admin.
