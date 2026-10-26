# Payment API v1 — contrat public (AfriPaie)

**Consommateur principal :** MHC (`apps/mhc/app/integrations/payment/`)
**Fournisseur :** AfriPaie — orchestrateur de paiement pan-africain (`PAYMENT_SERVICE_URL`, ex. https://afripaie.online)

**Authentification :** `Authorization: Bearer sk_test_…` / `sk_live_…`
(`PAYMENT_SERVICE_API_KEY`). Idempotence : en-tête `Idempotency-Key`.

## Encaissement — deux parcours

### 1. Push direct — `POST /v1/payments`

```json
{
  "reference": "MHC-SUB-42-P17",
  "amount": 25000,
  "currency": "XAF",
  "country": "CG",
  "channel": "mobile_money",
  "network": "MTN_CG",
  "customer": { "phone": "+24206000000", "email": "...", "name": "..." },
  "description": "Souscription MH-2026-0042",
  "metadata": { "payment_id": "17", "subscription_id": "42", "user_id": "7" },
  "return_url": "https://mhc…/payment-return.html"
}
```

- `amount` : **entier en unités mineures** (XAF/XOF → exposant 0).
- `country` facultatif : l'indicatif du `customer.phone` désigne le pays.
- Réponse : `{ "id": "pay_…", "status": "PROCESSING",
  "action": { "type": "ussd_push|redirect|none", "instructions|url": … },
  "provider": { "id": "…" } }`

### 2. Page hébergée — `POST /v1/checkout-sessions`

```json
{
  "reference": "MHC-SUB-42-P17",
  "amount": 25000, "currency": "XAF",
  "customer": { "email": "…" },
  "success_url": "https://mhc…/payment-return.html?result=success&payment_id=17",
  "cancel_url": "https://mhc…/payment-return.html?result=cancel&payment_id=17",
  "metadata": { "payment_id": "17", "subscription_id": "42" }
}
```

Réponse : `{ "id": "cs_…", "status": "OPEN", "url": "https://afripaie…/pay/<token>", "expires_at": "…" }`
→ rediriger l'assuré vers `url`. Le paiement créé depuis la page hérite de
`reference` et `metadata` (+ `afripaie_checkout_session`).

## Statut

`GET /v1/payments/{pay_…}` — interroge l'agrégateur et fait avancer l'état.
`GET /v1/checkout-sessions/{cs_…}` — session + `payment` complet associé.

Statuts AfriPaie → MHC : `CREATED|OPEN→pending`, `PROCESSING|AWAITING_CUSTOMER→processing`,
`SUCCEEDED|COMPLETED→success`, `FAILED→failed`, `EXPIRED|CANCELLED→expired`.

## Webhooks → MHC

Endpoint déclaré une fois via `POST /v1/webhook-endpoints` (scope `accounts:write`)
→ réponse contient `secret` (`whsec_…`, affiché une fois) → `PAYMENT_SERVICE_WEBHOOK_SECRET`.

MHC expose `POST /api/v1/payments/webhooks/afripaie`.

- Événements : `payment.succeeded` | `payment.failed` | `payment.expired`
- Corps : `{ "id": "evt_<res>_<type>", "type": "…", "data": <paiement complet> }`
- En-têtes : `Afripaie-Signature: t=<ts>,v1=<hmac-sha256(t.corps_brut)>`,
  `afripaie-event-id`, `afripaie-event-type`
- Tolérance horodatage : 5 min. Livraison « au moins une fois », sans ordre
  garanti — MHC se fie à l'état courant du `Paiement` (jamais écraser `valide`).

## Rapprochement MHC

`Paiement.reference_externe` = `pay_…` (direct) ou `cs_…` (checkout, remplacé
par le `pay_…` au premier webhook). Le rattachement utilise, dans l'ordre :
`data.id` == reference_externe → `data.metadata.payment_id` → référence
`MHC-SUB-<souscription>-P<paiement>`.

## Test

Clé `sk_test_…` + numéros simulateur (partie nationale à zéros, dernier
chiffre = issue : `0` succès, `2` refus, `7` expiration).
Ex. CI : `+2250000000000` succès, `+2250000000002` refus.
