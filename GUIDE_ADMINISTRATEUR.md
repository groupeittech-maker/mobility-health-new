# Guide Administrateur — Mobility Health Care

**Ordre de configuration de la plateforme, étape par étape.**

L'ordre ci-dessous respecte les dépendances réelles du système : chaque étape nécessite que les précédentes soient terminées. Ne pas sauter d'étape.

---

## Étape 0 — Compte administrateur

**Prérequis :** application installée et base migrée (voir `CONFIGURATION_APPLICATION.md`).

```bash
python scripts/create_admin_sql.py     # crée admin / admin123
```

Se connecter sur `login.html` → redirection vers `admin-dashboard.html`.
**Changer le mot de passe immédiatement.**

---

## Étape 1 — Pays de destination

*Pourquoi en premier : les produits, la tarification et les projets de voyage s'appuient sur ce référentiel.*

```bash
python scripts/init_destinations.py    # charge tous les pays + villes du monde
```

Puis dans **`admin-destinations.html`** :
- vérifier les pays chargés,
- garder activés uniquement les pays vendables.

---

## Étape 2 — Tarification

*Pourquoi maintenant : le calcul des primes utilise zones + durées + tranches d'âge + grilles de prix. Sans grille, aucun devis.*

Dans **`admin-tarification.html`** :
1. **Zones tarifaires** — rattacher chaque pays vendable à une zone (`INTRA_AFRIQUE`, `RSA_MAGHREB`, `EXTRA_AFRIQUE`, `INTER_AFRIQUE`, `FRANCE_UE`).
2. **Fenêtres de durée** — ex. 1–7 j, 8–15 j, 16–30 j…
3. **Tranches d'âge** — surprimes (< 18 ans, 70–75, 76–80, 81+).
4. **Grille de prix** — prix par zone × durée × âge.

Dans **`admin-tarification-frais.html`** : frais de service et taxes par pays assureur.

Vérification : `python scripts/check_tarification_destinations.py --strict`

---

## Étape 3 — Équipe interne Mobility Health

*Créer ces comptes dans **`admin-users.html`** — simple création, aucun rattachement requis.*

| # | Rôle à créer | Sa fonction |
|---|---|---|
| 1 | `production_agent` | Décision finale sur les dossiers, résiliations, souscription pour tiers |
| 2 | `medical_reviewer` | Revue médicale des dossiers + validation médicale des factures |
| 3 | `medecin_referent_mh` | Vérification des alertes SOS, validation rapports et factures (**utilise l'app mobile**) |
| 4 | `sos_operator` | Centre SOS temps réel, validation « sinistre » des factures |
| 5 | `agent_sinistre_mh` | Gestion des sinistres |
| 6 | `finance_manager` | Validation comptable, répartitions |
| 7 | `agent_comptable_mh` | Comptabilité MH |

> Le rôle `doctor` (médecin MH générique) est optionnel — il peut servir de repli dans les validations médicales.

---

## Étape 4 — Comptes agents assureur

*Toujours dans **`admin-users.html`** — créer les comptes AVANT les assureurs car ils seront rattachés à la fiche assureur.*

Créer **par assureur partenaire** :
- un compte `agent_comptable_assureur` (comptabilité),
- un compte `agent_sinistre_assureur` (sinistres + décisions de suspension/réémission de police),
- éventuellement un `production_agent` dédié à cet assureur.

---

## Étape 5 — Assureurs

Dans **`admin-assureurs.html`**, pour chaque assureur :
1. Créer la fiche (nom, pays, adresse, téléphone).
2. Uploader le **logo** (PNG/JPG).
3. **Rattacher les agents** créés à l'étape 4 dans les trois listes : *comptable*, *production*, *sinistre*.

Option démo : `python scripts/create_assureurs_and_products.py` crée 3 assureurs + 6 produits.

---

## Étape 6 — Comptes comptable courtier

Dans **`admin-users.html`** : créer un compte `agent_comptable_courtier` par courtier.

---

## Étape 7 — Courtiers

Dans **`admin-courtiers.html`** :
1. Créer le courtier (nom, pays, logo).
2. **Le rattacher à un assureur** (obligatoire).
3. Définir sa **commission %**.
4. Lier son **agent comptable** (compte créé à l'étape 6 — le système refuse tout autre rôle).

---

## Étape 8 — Hôpitaux

Dans **`admin-hospitals.html`**, pour chaque hôpital partenaire :
1. Créer la fiche : nom, ville, pays, adresse, **coordonnées GPS** (indispensables — l'hôpital le plus proche est choisi automatiquement lors d'un SOS), spécialités.
2. Désigner le **médecin référent MH** de l'hôpital (parmi les comptes `medecin_referent_mh` créés à l'étape 3) — il sera assigné en priorité aux sinistres de cet hôpital.

Option : `python scripts/seed_hospitals.py` (6 hôpitaux d'Abidjan avec GPS, à adapter).

---

## Étape 9 — Comptes du personnel hospitalier

Dans **`admin-users.html`**, créer pour **chaque hôpital** :

| Rôle | Fonction |
|---|---|
| `hospital_admin` | Gère l'établissement, les tarifs, les séjours |
| `agent_reception_hopital` | Accueille le sinistré, déclenche l'ambulance, ouvre le séjour |
| `medecin_hopital` | Rédige le rapport médical (un compte par médecin) |
| `agent_comptable_hopital` | Émet les factures |

⚠️ **Obligatoire : renseigner le champ « hôpital »** de chaque compte — sans ce rattachement, l'utilisateur ne peut rien voir ni faire.

---

## Étape 10 — Tarifs hospitaliers

Dans le portail hôpital (ou via `hospital_admin`) : renseigner les **tarifs des examens et actes** négociés — ils alimentent automatiquement les lignes de facture des séjours.

---

## Étape 11 — Produits d'assurance

*En dernier : un produit exige un assureur, des zones tarifaires et des prix.*

Dans **`admin-products.html`**, pour chaque produit :
1. Nom, description, **assureur porteur**, image.
2. **Zones géographiques** couvertes + pays exclus.
3. Limites : **âge min/max**, **durée max du voyage** (utilisées par le refus automatique).
4. Garanties (plafonds, franchises) et exclusions.
5. Tarifs produit (ou usage de la grille générale de l'étape 2).

---

## Étape 12 — Tests de bout en bout

| # | Test | Résultat attendu |
|---|---|---|
| 1 | Inscription d'un assuré (`register.html`) | Code e-mail → compte actif immédiat |
| 2 | Souscription complète | Dossier → décision auto → paiement → attestation + e-carte |
| 3 | Dossier à risque (ex. grossesse déclarée) | Routé en revue médicale → `medical_reviewer` notifié |
| 4 | Alerte SOS | Hôpital le plus proche + référent + agent sinistre notifiés |
| 5 | Séjour → rapport → facture | 3 validations → alerte « résolue » |

---

## Récapitulatif — l'ordre en une image

```
0  Admin
1  Pays de destination
2  Tarification (zones, durées, âges, prix, taxes)
3  Équipe interne MH (production, médical, référent, SOS, sinistre, finance)
4  Comptes agents assureur
5  Assureurs (+ rattachement agents)
6  Comptes comptable courtier
7  Courtiers (+ assureur + commission + agent)
8  Hôpitaux (+ GPS + médecin référent)
9  Personnel hospitalier (avec rattachement hôpital)
10 Tarifs hospitaliers
11 Produits d'assurance
12 Tests de bout en bout
```
