# Grille de test UAT — Application MyMHC

À remplir par l'équipe de test. Pour chaque scénario : ✅ conforme / ❌ non conforme (+ commentaire).
Priorités : **P0** bloquant, **P1** majeur, **P2** confort.

**Comptes de test nécessaires** : assuré avec police active · assuré sans police · médecin conseil MHC · agent production · agent finance · référent hôpital · souscripteur avec enfants.

---

## 1. Splash & démarrage

| # | Scénario | Étapes | Résultat attendu | P | ✓ |
|---|----------|--------|------------------|---|---|
| 1.1 | Animation de démarrage | Lancer l'app | Lignes du symbole apparaissent une à une, « MyMHC » en fondu (~1,4 s), « Strength for life. » au-dessus du bandeau bas, transitions douces | P2 | |
| 1.2 | Réduction animations système | Activer « supprimer animations » Android | Logo + signature affichés immédiatement | P2 | |
| 1.3 | Navigation rapide | Utilisateur connecté | Redirection accueil dès authentification, sans attendre la fin de l'animation | P1 | |
| 1.4 | Déconnecté | Utilisateur non connecté | Écran d'accueil/welcome | P1 | |
| 1.5 | Bandeau MHC | Bas de chaque écran | Bande graphique fine sur toutes les pages, y compris les pages poussées | P1 | |

## 2. Inscription

| # | Scénario | Étapes | Résultat attendu | P | ✓ |
|---|----------|--------|------------------|---|---|
| 2.1 | Inscription complète | Formulaire : identité, date naissance, sexe, nationalité+pays résidence (listes), téléphone, email, mot de passe | Compte créé, email de vérification envoyé | P0 | |
| 2.2 | Sélecteur pays | Cliquer « Sélectionner un pays » | Page recherche s'ouvre, **clavier ne masque pas la liste**, recherche insensible aux accents (« cote » → Côte d'Ivoire) | P0 | |
| 2.3 | Champs obligatoires | Soumettre incomplet | Messages « Requis » en ligne, pas d'envoi | P0 | |
| 2.4 | Email déjà utilisé | Email existant | Message « compte existant » clair | P1 | |
| 2.5 | Mot de passe faible | MDP non conforme | Règles affichées, refus | P1 | |
| 2.6 | Confirmation MDP | Deux MDP différents | Erreur de correspondance | P1 | |
| 2.7 | Téléphone par indicatif | Drapeau + numéro | Indicatif correct envoyé | P1 | |
| 2.8 | Vérification email | Lien/code reçu | Email validé → accès app | P0 | |
| 2.9 | Mot de passe oublié | « Mot de passe oublié » → email | Lien/code de réinitialisation, nouveau MDP actif | P0 | |
| 2.10 | CGU | Création sans accepter | Blocage | P1 | |

## 3. Connexion & session

| # | Scénario | Étapes | Résultat attendu | P | ✓ |
|---|----------|--------|------------------|---|---|
| 3.1 | Connexion valide | Email + MDP | Accueil affiché | P0 | |
| 3.2 | Mauvais identifiants | MDP erroné | Message d'erreur, pas de crash | P0 | |
| 3.3 | Session persistante | Fermer + rouvrir | Reste connecté | P1 | |
| 3.4 | Déconnexion | Compte → Déconnexion | Retour welcome, token supprimé | P1 | |
| 3.5 | Expiration token | Session expirée | Redirection login propre | P1 | |

## 4. Menu Compte

| # | Scénario | Résultat attendu | P | ✓ |
|---|----------|------------------|---|---|
| 4.1 | Contenu | Profil, Souscriptions, Paiements, Réclamations, Documents, Parrainage, Assistance, Déconnexion — **sans « Mes enfants » ni « Aide »** | P0 | |
| 4.2 | Navigation retour | Depuis un onglet Compte, flèche retour → **liste des onglets** (pas l'accueil) | P1 | |
| 4.3 | Photo de profil | Changer → mise à jour **immédiate** tiroir + dashboard, persistante | P1 | |

## 5. Profil

| # | Scénario | Résultat attendu | P | ✓ |
|---|----------|------------------|---|---|
| 5.1 | Structure | Mon voyage / Mon identité / Mes coordonnées / Enfants mineurs — sans Sécurité ni Déconnexion | P0 | |
| 5.2 | Voyage en cours | Destination + dates en **lecture seule** ; sans police → « Vous n'avez pas de voyage en cours. » | P0 | |
| 5.3 | Coordonnées | Téléphone/email/adresse postale éditables, sauvegarde persistée | P1 | |
| 5.4 | Identité | Modification → **réclamation** avec pièce jointe (pas d'édition directe) | P0 | |
| 5.5 | Sécurité | Écran changement mot de passe | P1 | |

## 6. Enfants mineurs

| # | Scénario | Résultat attendu | P | ✓ |
|---|----------|------------------|---|---|
| 6.1 | Ajout complet | Nom, prénom, naissance, nationalité (liste), **pays de résidence (liste)**, **lien obligatoire**, pièces | Enfant créé en liste | P0 | |
| 6.2 | Lien manquant | Sans lien → refus « lien requis » | P0 | |
| 6.3 | Majeur impossible | Date naissance ≥ 18 ans → refus | P0 | |
| 6.4 | Modification | Éditer → sauvegarde OK | P1 | |
| 6.5 | Suppression | Confirmer → retiré | P1 | |
| 6.6 | Pas de médical | Aucune question santé dans le formulaire enfant | P1 | |
| 6.7 | 18 ans atteint | Enfant retiré automatiquement, polices émises intactes | P0 | |

## 7. Tableau de bord

| # | Scénario | Résultat attendu | P | ✓ |
|---|----------|------------------|---|---|
| 7.1 | Sans couverture | « Pas de couverture », carte bénéficiaire nom/photo, CTA souscription | P0 | |
| 7.2 | E-carte active | Nom, N° police, validité, photo, **logo blanc**, fond officiel ; tappable → détail | P0 | |
| 7.3 | Carrousel | Plusieurs cartes → défilement horizontal | P1 | |
| 7.4 | Compteurs | En attente / Expirées / Attestations → listes filtrées | P1 | |
| 7.5 | Bande voyage | Destination, dates, durée, composition | P1 | |

## 8. Souscription — Étape 1 : Voyage

| # | Scénario | Résultat attendu | P | ✓ |
|---|----------|------------------|---|---|
| 8.1 | Plage de dates | Sélecteur natif : chiffres **blancs** sur bandes violettes | P1 | |
| 8.2 | Date passée | Départ < aujourd'hui → refus | P0 | |
| 8.3 | > 92 jours | Refus « limitée à 92 jours » | P0 | |
| 8.4 | Destination | Liste référentiel + recherche | P0 | |
| 8.5 | Adulte + enfants profil | Enfants du profil cochés, pièces rappelées | P0 | |
| 8.6 | Nouvel enfant flux | Pièces (passeport + photo) requises | P0 | |
| 8.7 | Passeport < retour | **Blocage** « expire avant la fin du voyage » (adulte + enfants) | P0 | |
| 8.8 | Enfant majeur en cours | 18 ans avant date retour → **blocage** | P0 | |
| 8.9 | Enfants seuls | Adulte décoché : bandeau mineurs, accompagnant + autorisation + pièce parent obligatoires | P0 | |
| 8.10 | Composition affichée | X adultes, Y enfants conformes | P1 | |

## 9. Souscription — Étape 2 : Questionnaire médical

| # | Scénario | Résultat attendu | P | ✓ |
|---|----------|------------------|---|---|
| 9.1 | Par personne | « Oui » → choix des personnes concernées + précision | P0 | |
| 9.2 | Précision vide | « Veuillez préciser » bloque | P0 | |
| 9.3 | Un « oui » | Dossier complet → pôle santé | P0 | |
| 9.4 | Grossesse ≤ 5 mois | → pôle santé (pas refus auto) | P0 | |
| 9.5 | Grossesse > 5 mois | **Refus de tout le dossier**, y compris enfant | P0 | |
| 9.6 | Enfant | Mêmes questions que l'adulte | P1 | |
| 9.7 | Tout « Non » | Passage assurance | P0 | |

## 10. Souscription — Étape 3 : Assurance

| # | Scénario | Résultat attendu | P | ✓ |
|---|----------|------------------|---|---|
| 10.1 | Détails produit | **Bottom-sheet** (pas page) | P0 | |
| 10.2 | Exclusions | « J'ai lu les exclusions » obligatoire | P0 | |
| 10.3 | CGU non cochées | Continuer grisé | P0 | |
| 10.4 | Boutons | « Sélectionner » + « Continuer » **violets** | P1 | |
| 10.5 | Choix produit | → récapitulatif | P0 | |

## 11. Souscription — Étape 4 : Récapitulatif, décision, paiement

| # | Scénario | Résultat attendu | P | ✓ |
|---|----------|------------------|---|---|
| 11.1 | Récap | Voyageurs, dates, destination, montant détaillé | P1 | |
| 11.2 | Retour étape | « Étape précédente » → données conservées | P0 | |
| 11.3 | Décision OK | → « À payer », écran paiement | P0 | |
| 11.4 | Attente validation | Suspicion médicale → « transmis » + pas de paiement + retour accueil | P0 | |
| 11.5 | Refus | Bloc refusé + motifs + **bouton retour accueil** | P0 | |
| 11.6 | Paiement | PSP lancé, statut suivi, **attestation émise** après succès | P0 | |
| 11.7 | Abandon PSP | « Vérifier le statut » + historique | P1 | |
| 11.8 | Montants | Prime + chargement + total conformes à la simulation | P1 | |
| 11.9 | Plusieurs enfants | Tous listés au récap | P1 | |

## 12. eKYC

| # | Scénario | Résultat attendu | P | ✓ |
|---|----------|------------------|---|---|
| 12.1 | Déclenchement | Selon paramétrage → flux eKYC avant finalisation | P0 | |
| 12.2 | Vérification doc | Passeport/ID → statut accepté | P0 | |
| 12.3 | NFC passeport | Lecture NFC du passeport → données récupérées | P1 | |
| 12.4 | Échec eKYC | Session rejetée → dossier → **revue production** (pas refus auto) | P0 | |
| 12.5 | Coût | eKYC facturée 350 FCFA/dossier, déduite part MHC | P1 | |
| 12.6 | Statuts | Sessions en attente bloquent la finalisation | P1 | |

## 13. Listes de souscriptions

| # | Scénario | Résultat attendu | P | ✓ |
|---|----------|------------------|---|---|
| 13.1 | Onglet actif | **Seule la police active** visible | P0 | |
| 13.2 | En attente | Brouillons + « À payer » | P1 | |
| 13.3 | Supprimer brouillon | OK | P1 | |
| 13.4 | Supprimer « À payer » | Session PSP abandonnée → OK | P0 | |
| 13.5 | Suppression avec paiement | Refus | P0 | |
| 13.6 | Détail | Destination, dates, montant, médecin-conseil tél. | P1 | |

## 14. Actions sur police — avenants

| # | Scénario | Résultat attendu | P | ✓ |
|---|----------|------------------|---|---|
| 14.1 | Annulation simulée | Ristourne estimée affichée avant confirmation | P1 | |
| 14.2 | Annulation | Avenant **102** ; bandeau « Annulation en cours de traitement » ; autres actions grisées | P0 | |
| 14.3 | Modif. destination | Avenant **107**, même zone → pas de complément | P0 | |
| 14.4 | Modif. dates + | Complément calculé → paiement → quittance **119** | P0 | |
| 14.5 | Modif. dates − | Ristourne calculée → remboursement → quittance **120** | P0 | |
| 14.6 | Modif. après départ | Refus | P0 | |
| 14.7 | Prorogation | Avenant **108** attente paiement → couverture étendue après règlement | P0 | |
| 14.8 | 2ᵉ demande | Refus + actions désactivées tant qu'une demande est en cours | P0 | |
| 14.9 | Abandon | Actions débloquées | P1 | |
| 14.10 | Documents | PDF avenants + quittances téléchargeables | P0 | |

## 15. Sinistres & réclamations

| # | Scénario | Résultat attendu | P | ✓ |
|---|----------|------------------|---|---|
| 15.1 | Déclarer sinistre | Formulaire + pièces → enregistré | P0 | |
| 15.2 | Réclamation + PJ | Catégorie + message + pièces jointes | P0 | |
| 15.3 | Catégorie identité | « Modification de mes informations personnelles » dispo | P0 | |
| 15.4 | Chronologie | Historique des événements visibles | P1 | |
| 15.5 | Contestation | Clôturée ≤ 1 mois → réouverture ; > 1 mois → masquée | P1 | |
| 15.6 | Prise en charge hôpital | Référent valide actes/examens → statut suivi | P0 | |
| 15.7 | Factures hôpital | Facture créée, items détaillés | P1 | |
| 15.8 | Flux complet | Déclaration → soins → facture → règlement | P0 | |

## 16. Téléconsultation / Hôpitaux / SOS

| # | Scénario | Résultat attendu | P | ✓ |
|---|----------|------------------|---|---|
| 16.1 | Téléconsult. | Médecin conseil du **pays de la police active** uniquement | P0 | |
| 16.2 | Sans police | Message aucun médecin affecté | P1 | |
| 16.3 | Hôpitaux | Liste filtrée au **pays destination** de la police | P0 | |
| 16.4 | SOS formulaire | **Pas de « Décrivez votre situation »** ; géoloc ou adresse/repère | P0 | |
| 16.5 | SOS envoi | Alerte + coordonnées transmises | P0 | |
| 16.6 | SOS sans GPS | Adresse manuelle obligatoire | P1 | |

## 17. Documents & attestations

| # | Scénario | Résultat attendu | P | ✓ |
|---|----------|------------------|---|---|
| 17.1 | Attestation valide | PDF téléchargeable | P0 | |
| 17.2 | Expirée/résiliée | Visible + téléchargeable **1 an** puis archivée | P1 | |
| 17.3 | E-carte | Logo **blanc**, fond officiel, photo bas-droite | P1 | |
| 17.4 | Quittances | 119 (règlement) + 120 (ristourne) téléchargeables | P0 | |

## 18. UI / UX transverse

| # | Scénario | Résultat attendu | P | ✓ |
|---|----------|------------------|---|---|
| 18.1 | Bandeau | Présent sur **toutes** les pages, hauteur fine | P1 | |
| 18.2 | Boutons | Violet `#4e267c` partout | P1 | |
| 18.3 | Texte sur violet | Dates/chiffres en blanc | P1 | |
| 18.4 | Retour | Toujours page précédente | P0 | |
| 18.5 | Pays | Listes/recherche, pas de champs libres | P1 | |
| 18.6 | Clavier | Ne masque pas le contenu | P1 | |
| 18.7 | Hauteurs | Éléments compacts | P2 | |

## 19. Sécurité & cas limites

| # | Scénario | Résultat attendu | P | ✓ |
|---|----------|------------------|---|---|
| 19.1 | Hors-ligne | Messages propres, retry, pas de crash | P0 | |
| 19.2 | 4xx/5xx | Messages utilisateur compréhensibles | P1 | |
| 19.3 | Rotation | État conservé | P2 | |
| 19.4 | Permissions | GPS/photo/caméra demandés au bon moment | P1 | |
| 19.5 | Données sensibles | Pas de secrets affichés/logs | P0 | |

---

## Synthèse des résultats

| Section | Scénarios | P0 | P1 | P2 | Réussis | Échoués | % |
|---------|-----------|----|----|----|---------|---------|---|
| 1. Splash | 5 | | | | | | |
| 2. Inscription | 10 | | | | | | |
| 3. Connexion | 5 | | | | | | |
| 4. Compte | 3 | | | | | | |
| 5. Profil | 5 | | | | | | |
| 6. Enfants | 7 | | | | | | |
| 7. Dashboard | 5 | | | | | | |
| 8. Voyage | 10 | | | | | | |
| 9. Questionnaire | 7 | | | | | | |
| 10. Assurance | 5 | | | | | | |
| 11. Récap/paiement | 9 | | | | | | |
| 12. eKYC | 6 | | | | | | |
| 13. Listes | 6 | | | | | | |
| 14. Avenants | 10 | | | | | | |
| 15. Sinistres | 8 | | | | | | |
| 16. Téléconsult./SOS | 6 | | | | | | |
| 17. Documents | 4 | | | | | | |
| 18. UI | 7 | | | | | | |
| 19. Sécurité | 5 | | | | | | |
| **Total** | **~123** | | | | | | |

## Journal des anomalies

| # | Scénario | Sévérité | Description | Build | Statut |
|---|----------|----------|-------------|-------|--------|
| | | | | | |
