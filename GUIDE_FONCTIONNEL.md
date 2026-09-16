# Mobility Health Care — Guide fonctionnel complet

---

## 1. Qu'est-ce que Mobility Health Care ?

Plateforme d'**assurance voyage santé** qui couvre tout le cycle de vie d'un contrat :

```
Souscription → Examen du dossier (AVANT paiement) → Paiement → Attestation + carte d'assuré
            → Alerte SOS → Prise en charge hospitalière → Facture à triple validation
            → Répartition financière (assureur / courtier / MH)
```

**Deux canaux :**
- **Portail web** — tous les profils (assuré, équipe MH, hôpital, assureur, courtier, comptables).
- **Application mobile** — deux profils uniquement : l'**assuré** (souscription, SOS, attestations) et le **médecin référent MH** (pipeline sinistre).

---

## 2. Les profils et leurs rôles

### 2.1 Le client

| Profil | Ce qu'il fait |
|---|---|
| **Assuré** | S'inscrit (activation immédiate par code e-mail), remplit son dossier de voyage, paie, reçoit attestation + e-carte, déclenche des alertes SOS géolocalisées, demande suspensions et résiliations. Peut souscrire **pour un enfant mineur bénéficiaire** (le parent souscrit, l'enfant voyage). |

### 2.2 Équipe Mobility Health (MH)

| Profil | Rôle |
|---|---|
| **Administrateur** | Gère tout : utilisateurs, produits, tarifs, assureurs, courtiers, hôpitaux, destinations, statistiques, sinistres. |
| **Relecteur médical** | Statue sur les dossiers en **revue médicale** (grossesse, maladie déclarée, âge ≥ 70 ans). Valide médicalement les factures. |
| **Médecin référent MH** | Pilote médical des sinistres sur mobile : **vérifie la véracité de chaque alerte** (déclenche officiellement la prise en charge), valide les rapports hospitaliers, les bons et les factures. |
| **Agent de production** | Statue sur les dossiers en **revue production** (séjour long, groupe, gros montant), traite les résiliations, peut souscrire pour un tiers. |
| **Opérateur SOS / Gestionnaire sinistre MH** | Surveille les alertes en temps réel, suit le dossier sinistre, valide les factures côté « sinistre », clôture les dossiers. |
| **Responsable financier / Comptable MH** | Validation comptable des factures, répartition des montants, remboursements. |

### 2.3 Partenaires

| Profil | Rôle |
|---|---|
| **Agent sinistre assureur** | Suit les sinistres de son assureur ; **décide des suspensions et réémissions de police**. |
| **Comptable assureur / courtier** | Consulte la comptabilité de son organisation (primes, sinistres, commissions). |
| **Admin hôpital** | Configure l'établissement : tarifs d'actes/examens, équipe. |
| **Agent de réception hôpital** | Reçoit le sinistré, déclenche l'ambulance, ouvre le séjour, l'oriente vers un médecin. |
| **Médecin de l'hôpital** | Soigne le patient et rédige le rapport médical (motif, actes, examens, durée). |
| **Comptable hôpital** | Émet la facture du séjour après validation du rapport. |

---

## 3. Workflow 1 — Création du compte assuré

```
Assuré s'inscrit → Code à 6 chiffres par e-mail (15 min) → Saisie du code / clic sur le lien
                 → COMPTE ACTIF → Connexion
```

| Acteur | Action | Document produit |
|---|---|---|
| Assuré | Remplit le formulaire (identité, contact d'urgence, mot de passe) | — |
| Système | Envoie le code de vérification | 📄 E-mail de vérification |
| Assuré | Saisit le code ou clique le lien | — |
| Système | Active le compte **immédiatement** | — |

> ⚠️ **Pas d'approbation humaine** pour l'inscription d'un assuré (flux actuel). Les comptes internes et partenaires sont créés par l'administrateur et sont actifs dès création.

---

## 4. Workflow 2 — Souscription

```
Voyage → Produit + prix → Questionnaires → SOUMISSION → Décision automatique
   → (revues humaines si requis) → Paiement → Contrat ACTIF + documents
```

### Étape 1 — Dossier de voyage
- **Acteur :** Assuré
- **Action :** destination, dates, transport, participants ; pièces justificatives ; possibilité de déclarer un voyageur tiers (enfant bénéficiaire).
- **📄 Documents :** pièces jointes fournies par l'assuré (passeport, CNI, justificatif de résidence, réservation).

### Étape 2 — Produit et prix
- **Acteur :** Assuré
- **Action :** choix du produit → prix calculé automatiquement (zone × durée × âge + surprimes < 18 ans et ≥ 70 ans + frais de service + taxes par pays).
- **📄 Documents :** devis affiché (plusieurs devis comparables).

### Étape 3 — Questionnaires
- **Acteur :** Assuré
- **Action :** questionnaire **administratif** + questionnaire **médical** (obligatoire). Étapes verrouillées après soumission.
- **📄 Documents :** questionnaires enregistrés et versionnés (chaque nouvelle version archive la précédente) + notification de confirmation.

### Étape 4 — Soumission → décision automatique
- **Acteur :** Assuré soumet → **moteur de décision** évalue immédiatement.

**Trois issues :**

| Issue | Conditions | Suite |
|---|---|---|
| ❌ **Refus immédiat** | Souscripteur mineur · âge hors limites produit · **grossesse > 5 mois** · durée > max · destination exclue · maladie à exclusion (dialyse, cancer actif, sida, greffe récente…) | Dossier refusé, jamais débité |
| 👁 **Revue humaine** | *Médicale* : grossesse ≤ 5 mois, âge ≥ 70 ans, maladie/traitement déclaré, voyage à but médical. *Production* : séjour > 30 j, plusieurs participants, montant > 200 000 FCFA, groupe, entreprise, sport extrême | Étape 5 |
| ✅ **Approbation auto** | Aucun critère de risque | Directement « attente de paiement » |

- **📄 Documents :** notifications aux relecteurs ; notification client du résultat.

### Étape 5 — Revues humaines (si requises)
- **Acteurs :** Relecteur médical → Agent de production (dans cet ordre)
- **Action :** chacun approuve ou refuse ; un seul refus rejette le dossier.
- **📄 Documents :** notification client — *« dossier approuvé, paiement disponible »* ou *« dossier refusé »* (avec motif).

### Étape 6 — Paiement
- **Acteur :** Assuré
- **Action :** paiement possible **uniquement si le dossier est approuvé**. Reprise possible depuis l'historique (« Reprendre »). Sur mobile, le paiement déclenche l'évaluation si le dossier n'a pas été soumis.
- **📄 Documents :** transaction enregistrée (référence unique).

### Étape 7 — Contrat actif

Le paiement confirmé rend le contrat **actif** et émet :

| 📄 Document | Code | Contenu |
|---|---|---|
| **Attestation d'assurance définitive** | 101 | PDF officiel + QR code — vérifiable publiquement (aéroport, ambassade, hôpital) |
| **E-carte d'assuré** | — | Carte numérique : photo, QR code, n° de police |
| **Quittance de règlement** | 119 | Reçu officiel du paiement de la prime |
| **Numéro de police** | 10 | Référence structurée ordre-pays-assureur-année |

> **Point clé : plus d'attestation provisoire.** Toutes les validations humaines ont lieu *avant* le paiement ; le paiement délivre directement l'attestation définitive. Une analyse documentaire automatique tourne ensuite en arrière-plan pour les équipes internes.

---

## 5. Workflow 3 — Vie du contrat

### 5.1 Suspension de police

```
Assuré demande (motif + pièces) → Assureur approuve/refuse → si approuvé : suspension
→ plus tard : Assureur réémet la police
```

| Acteur | Action | 📄 Document produit |
|---|---|---|
| Assuré | Demande avec motif + justificatifs | Pièces jointes à la demande |
| Agent sinistre **assureur** | Approuve ou refuse | **Avenant de suspension (105)** si approuvé |
| Agent sinistre assureur | Lève la suspension | **Avenant de réémission (106)** |

*Chaque avenant est un PDF téléchargeable, régénéré à jour à chaque consultation.*

### 5.2 Résiliation

```
Assuré demande → Agent de production approuve/refuse → si approuvé : contrat résilié
```

| Acteur | Action | 📄 Document produit |
|---|---|---|
| Assuré | Demande de résiliation | — |
| **Agent de production** | Approuve ou refuse | Si approuvé : **avenant d'annulation (102)** + remboursement — le courtier rend toute sa commission, l'assureur rend la prime, **MH conserve 30 % de la prime** |

---

## 6. Workflow 4 — Sinistre SOS (les 15 étapes réelles)

**Condition préalable :** souscription **active** + attestation définitive **valide** — sinon l'alerte est refusée dès le départ.

| # | Étape | Acteur | 📄 Document produit |
|---|---|---|---|
| 1 | Alerte déclenchée (GPS auto) | Assuré | Numéro d'alerte unique |
| 2 | Centre des opérations alerté — sinistre créé | Système | — |
| 3 | Médecin référent notifié | Système (assignation auto) | Notification push SOS détaillée |
| 4 | Localisation de l'assuré | Système | — |
| 5 | Hôpital le plus proche activé | Système (géoloc) | Notification réception hôpital |
| 6 | Ambulance en route | Réception hôpital | — |
| 7 | Médecin référent en route | Médecin référent | — |
| 8 | Partage des données médicales | Système | Accès sécurisé aux infos de l'assuré |
| 9 | **Vérification de la véracité** — *étape clé* | **Médecin référent** | — |
| 10 | Si fausse alerte → suspension | Médecin référent | 📄 **BRPCU — bon de refus (112)** + sinistre annulé |
| 11 | Si urgence avérée → validation | Médecin référent | 📄 **N° de sinistre officiel (11)** + **BPCU — bon de prise en charge (111, valable 24 h)** + notification réception |
| 12 | Ouverture du séjour + orientation médecin | Réception hôpital | 📄 Fiche de séjour (service, chambre, médecin assigné) — *impossible avant l'étape 11* |
| 13 | Rapport médical → validation | Médecin hôpital → Médecin référent | 📄 **Rapport médical du séjour** (motif, durée, actes, examens) |
| 14 | Facture + triple validation | Comptable hôpital → référent → agent sinistre → comptable MH | 📄 **Facture hospitalière** (lignes aux tarifs négociés + TVA) |
| 15 | Clôture | Système | 📄 Répartition comptable assureur / courtier / MH — alerte « résolue » |

### 6.1 La chaîne des bons de prise en charge

Au-delà du BPCU, des bons officiels jalonnent le parcours du patient. Chaque bon est un **PDF numéroté selon la nomenclature MHC**, certains exigeant une **double validation**.

| 📄 Document | Code | Émis par | Validations requises | Validité |
|---|---|---|---|---|
| **BPCU** — prise en charge d'urgence | 111 | Médecin référent (auto à la validation) | — | 24 h |
| **BRPCU** — refus de prise en charge | 112 | Médecin référent (auto au rejet) | — | — |
| **BH** — hospitalisation | 113 | Hôpital | Médecin-conseil + Pôle médical MHC | 72 h |
| **BPH** — prolongation d'hospitalisation | 117 | Hôpital | Médecin-conseil + Pôle médical MHC | 24 h |
| **BS** — bulletin de sortie | 114 | Hôpital | — | — |
| **BRS** — rapatriement sanitaire | 115 | Auto (avec BS mode rapatriement) | Pôle médical MHC + Partenaire santé | — |
| **BRF** — rapatriement funéraire | 116 | Médecin-conseil | Pôle médical MHC | — |
| **ARS** — retour rapatriement sanitaire | 121 | Pôle médical MHC | — **(clôture)** | — |
| **ARF** — rapatriement funéraire | 122 | Pôle médical MHC | — **(clôture)** | — |
| Certificat de décès | 118 | Upload hôpital / référent | — | — |

**Enchaînement des bons :**

```
Alerte vérifiée → BPCU (ou BRPCU si refus)
   BPCU → BH / BS / BRF
   BH ou BPH → BPH (prolongation) / BS / BRF
   BS mode "rapatriement sanitaire" → + BRS automatique → ARS (clôture) ou BRF
   BRF (décès, à tout moment) → ARF (clôture)
   ARS ou ARF = dossier documentaire clôturé définitivement
```

---

## 7. Scénarios possibles — issues et documents

### 7.1 Souscription

| Scénario | Issue | 📄 Documents produits |
|---|---|---|
| Dossier standard | Approbation auto → paiement → contrat actif | Attestation (101) + e-carte + quittance (119) |
| Grossesse ≤ 5 mois / ≥ 70 ans / maladie déclarée | Revue médicale → production si besoin | Mêmes documents si approuvé |
| Long séjour / groupe / gros montant / sport extrême | Revue production | Mêmes documents si approuvé |
| Grossesse > 5 mois, âge hors limites, maladie exclue, destination exclue | **Refus automatique** avant paiement | Notification de refus motivée |
| Refus en revue | Dossier refusé — jamais débité | Notification de refus avec motif |
| Dossier interrompu | Reprise depuis l'historique | — |
| Voyage d'un enfant seul | Parent majeur souscrit pour l'enfant | Attestation au nom de l'enfant bénéficiaire |
| Suspension de police | Assuré demande → assureur décide | Avenant suspension (105) → réémission (106) |
| Résiliation | Assuré demande → production traite | Avenant d'annulation (102) + remboursement (MH garde 30 %) |

### 7.2 Sinistre

| Scénario | Issue | 📄 Documents produits |
|---|---|---|
| Urgence avérée | Prise en charge complète | BPCU (111) → BH (113) → rapport → facture → BS (114) → 3 validations → résolu |
| Séjour prolongé | Prolongation d'hospitalisation | BPH (117) par période de 24 h |
| **Fausse alerte** | Sinistre annulé | BRPCU (112) |
| Rapport médical refusé | Correction par le médecin hospitalier | Rapport corrigé resoumis |
| Facture refusée | Rejetée à l'étape concernée | Facture rejetée + historique |
| Sortie ambulatoire / transfert / guérison | Modes de sortie | BS (114) avec mode de sortie |
| Rapatriement sanitaire | Retour organisé par MH | BS + BRS (115) → ARS (121) au retour |
| **Décès** | Branche parallèle, possible à tout moment | Certificat de décès (118) + BRF (116) → ARF (122) — dossier clôturé |
| Pas de souscription active ou d'attestation | **SOS impossible** | Message de refus |

---

## 8. Récapitulatif documentaire complet

### Documents de police (cycle souscription)

| Code | Document | Moment d'émission |
|---|---|---|
| 10 | Numéro de police | À la souscription |
| 101 | **Attestation d'assurance** | Après paiement confirmé |
| — | **E-carte d'assuré** (image + QR) | Avec l'attestation |
| 119 | **Quittance de règlement** | Après paiement |
| 102 | Avenant d'annulation | Résiliation approuvée |
| 105 | Avenant de suspension | Suspension approuvée par l'assureur |
| 106 | Avenant de réémission | Levée de suspension par l'assureur |
| 103 | Bon de résiliation | (nomenclature prévue) |
| 104 | Bon de renouvellement | (nomenclature prévue) |

### Documents de sinistre (cycle SOS / hospitalier)

| Code | Document | Émis par | Validations |
|---|---|---|---|
| 11 | Numéro de sinistre | Automatique à la vérification | — |
| 111 | BPCU — prise en charge urgence | Médecin référent (auto) | — |
| 112 | BRPCU — refus de prise en charge | Médecin référent (auto) | — |
| 113 | BH — hospitalisation | Hôpital | Médecin-conseil + Pôle médical MHC |
| 117 | BPH — prolongation | Hôpital | Médecin-conseil + Pôle médical MHC |
| 114 | BS — bulletin de sortie | Hôpital | — |
| 115 | BRS — rapatriement sanitaire | Auto (avec BS rapatriement) | Pôle médical MHC + Partenaire santé |
| 116 | BRF — rapatriement funéraire | Médecin-conseil | Pôle médical MHC |
| 121 | ARS — retour rapatriement sanitaire | Pôle médical MHC | — (clôture) |
| 122 | ARF — rapatriement funéraire | Pôle médical MHC | — (clôture) |
| 118 | Certificat de décès | Upload hôpital / référent | — |
| — | Rapport médical de séjour | Médecin hospitalier | Médecin référent |
| — | Facture hospitalière | Comptable hôpital | Médicale + sinistre + comptable |

---

## 9. Qui fait quoi — résumé

| Action | Qui |
|---|---|
| Dossier, paiement, SOS, suspension, résiliation | Assuré |
| Revue médicale du dossier | Relecteur médical / médecin référent |
| Revue production du dossier | Agent de production |
| Vérification de l'urgence + BPCU/BRPCU + validation rapports, factures, bons | Médecin référent MH |
| Séjour, ambulance, orientation, BS, BH, BPH | Réception / admin hôpital |
| Rapport médical | Médecin de l'hôpital |
| Facture du séjour | Comptable hôpital |
| Validation sinistre de la facture | Opérateur SOS / gestionnaire sinistre |
| Validation comptable + répartition | Comptable MH / responsable financier |
| Suspensions et réémissions | Agent sinistre assureur |
| Résiliations | Agent de production |
| ARS / ARF (clôture documentaire) | Pôle médical MHC |
