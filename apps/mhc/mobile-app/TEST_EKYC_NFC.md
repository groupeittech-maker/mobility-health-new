# Test eKYC — lecture NFC du passeport

## Prérequis

- Téléphone Android avec NFC (API 24+) ou iPhone 7+ (iOS 15+)
- Un passeport électronique réel (symbole puce sur la couverture)
- Backend MHC démarré + plateforme Trusdy eKYC accessible (`EKYC_*` configurés, mode `live` ou `stub`)
- APK debug : `flutter build apk --debug` → `build/app/outputs/flutter-apk/app-debug.apk`

## Parcours de test

1. **Entrée** — Profil → Paramètres → *Vérification d'identité (eKYC)*.
   L'écran hub crée la session via `POST /api/v1/ekyc/sessions` et reçoit
   la `verification_url`.

2. **Parcours web** — « Continuer dans le navigateur sécurisé » ouvre l'UI
   hébergée : consentement → photo du document → selfie → OTP envoyé au
   numéro du compte (l'utilisateur ne peut pas en changer).

3. **Lecture NFC** — « Lire la puce NFC du passeport » :
   - soit « Scanner la zone MRZ » (caméra, extraction locale — rien n'est
     envoyé) : numéro + dates pré-remplis ;
   - soit saisie manuelle des 3 champs BAC.
   Poser le passeport sous le téléphone, ne pas bouger jusqu'à la fin.
   Ordre d'authentification : PACE si la puce l'annonce, sinon BAC.

4. **Verdict** — l'app envoie EF.COM/SOD/DG1/DG2 bruts au serveur qui refait
   toute l'authentification passive :
   - `VALID` → check NFC PASSED ;
   - `INVALID` → dossier bloqué (preuve de fraude) ;
   - `INDETERMINATE` (CSCA inconnu, SOD malformé) → revue manuelle.

5. **Vérification du résultat** — le hub rafraîchit le statut toutes les 4 s ;
   côté back-office, `GET /ekyc/sessions/{id}` montre le verdict appliqué
   (identité enrichie, souscription validée ou refusée).

## Cas à couvrir

| Cas | Attendu |
|---|---|
| Passeport posé correctement, MRZ exact | `VALID` |
| Numéro de document saisi faux | `BAC_FAILED` — clés refusées, réessayer |
| Passeport retiré en cours de lecture | erreur « gardez le passeport immobile » |
| Passeport non électronique | EF.COM/CardAccess absent → erreur de lecture |
| CSCA non présent dans le magasin serveur | `INDETERMINATE` → REVIEW (pas rejet) |
| `DG1` forgé (hash modifié) | `INVALID` → session REJECTED |

## Limites connues

- Carte d'identité CNI : la lecture NFC des cartes ID n'est pas couverte
  (protocole différent de l'eMRTD) — le parcours web sans NFC reste la voie.
- iOS : le scaffold `ios/` est généré avec l'entitlement NFC, mais un build
  iOS n'a pas été validé faute de macOS/Xcode.
