# Interactions Mobile ↔ Back-office — Point synthétique

## Les deux canaux et leurs utilisateurs

| Canal | Utilisateurs | Périmètre |
|---|---|---|
| **Mobile** | Assuré + Médecin référent MH | Actions terrain : souscrire, payer, SOS, valider médicalement |
| **Web back-office** | Toute l'équipe MH + partenaires (hôpital, assureur, courtier) | Revue, pilotage, administration, comptabilité |

---

## 1. Boucle souscription

```
MOBILE (assuré)                   BACK-OFFICE (équipe MH)
─────────────────                 ─────────────────────────
Voyage + questionnaires
  └─► "Soumettre le dossier" ──►  Revue médicale (medical-review)
                              ──► Revue production (production-review)
  ◄── Push "approuvé / refusé" ◄──
Paiement ──────────────────────►  Attestation + e-carte + quittance
Attestation visible               │ dossier visible dans admin-subscriptions
```

- Le mobile **déclenche** l'évaluation (bouton « soumettre », ou tentative de paiement si dossier non soumis).
- Le back-office **décide** : relecteur médical puis agent de production.
- Le mobile **reçoit** le verdict par push, ce qui débloque le paiement.

## 2. Boucle sinistre — le cœur des interactions

```
MOBILE                              BACK-OFFICE WEB
────────────────────────────────    ──────────────────────────────────────────
Assuré : bouton SOS + GPS      ──►  Dashboard SOS : alerte temps réel (WebSocket + son)
                                    sinistre auto-créé + hôpital le plus proche assigné
                                    notifications agent sinistre + réception hôpital
Référent : « Sinistre à valider »◄──
  vérifie l'urgence            ──►  vrai → n° sinistre + BPCU
                                    faux → annulé + BRPCU
                                    Réception : ouvre séjour → médecin hôpital
                                    Médecin hôpital : rapport médical
Référent : « Rapport à valider »◄── rapport soumis
  valide le rapport            ──►  Comptable hôpital notifié → émet la facture
Référent : « Facture à valider »◄── facture émise
  validation médicale          ──►  Agent sinistre : validation sinistre
                                  ──► Comptable MH : validation comptable
Référent : onglet « Résolu »   ◄──  alerte résolue + répartition financière
```

> Le mobile du référent est un **pipeline à 4 onglets** — Sinistre / Rapport / Facture / Résolu — chacun avec « À valider » / « Validé ». Chaque action back-office fait avancer le dossier d'un onglet à l'autre.

## 3. Matrice des interactions

| Événement mobile | Effet back-office | Retour vers mobile |
|---|---|---|
| Assuré soumet dossier | File de revue médicale / production | Push résultat |
| Assuré paie | Paiement validé, écritures comptables | Attestation + e-carte |
| Assuré déclenche SOS | Alerte carte SOS, sinistre créé, hôpital assigné | Suivi dans historique |
| Assuré demande suspension | File décision de l'assureur | Avenant (105 / 106) |
| Assuré demande résiliation | File agent de production | Avenant annulation (102) + remboursement |
| Référent valide l'urgence | N° sinistre + BPCU émis, réception notifiée | Onglet suivant du pipeline |
| Référent valide le rapport | Comptable hôpital autorisé à facturer | Onglet « Facture » |
| Référent valide la facture | File validation sinistre puis comptable | Onglet « Résolu » |

## 4. Canaux de notification

| Canal | Mobile | Back-office |
|---|---|---|
| **Push FCM** | SOS, rapports, factures (référent) ; décisions dossier, rappels questionnaires (assuré) | — |
| **Notifications in-app** | ✔ | ✔ tous les portails |
| **WebSocket `/ws/sos`** | — | Dashboard SOS temps réel (carte + son d'alerte) |
| **E-mail / SMS** | ✔ | ✔ |

## 5. Règle de partage des tâches

- **Mobile = action de terrain et validation médicale** : l'assuré agit (souscrire, SOS), le référent tranche médicalement (urgence, rapport, facture, bons).
- **Back-office = décision administrative et financière** : revue production, assignations, facturation, comptabilité, répartition.
- **Point de bascule unique** : le médecin référent est le seul profil des deux côtés — sa validation mobile déclenche ce que tout le back-office exécute ensuite (numéro de sinistre → séjour → facture → paiement).
