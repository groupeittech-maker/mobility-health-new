# Payment API v1 — contrat public

**Consommateur principal :** MHC (`apps/mhc/app/integrations/payment/`)

## Endpoints

### POST /v1/payments/intents

Crée une intention de paiement.

**Request :**
```json
{
  "amount": 25000,
  "currency": "XAF",
  "country": "CG",
  "reference": "MHC-SUB-2026-0042",
  "method": "mobile_money",
  "customer": { "phone": "+242...", "email": "..." },
  "callback_url": "https://mhc.../api/v1/webhooks/payment",
  "metadata": {}
}
```

**Response :**
```json
{
  "payment_id": "pay_abc123",
  "status": "pending",
  "provider": "mtn_cg",
  "checkout_url": null,
  "expires_at": "2026-09-01T12:00:00Z"
}
```

### GET /v1/payments/{payment_id}

Retourne le statut d'une transaction.

### Webhook → MHC

`POST {callback_url}` — événements : `payment.success`, `payment.failed`, `payment.expired`.

**Authentification :** Bearer API key ou signature HMAC (à définir avec l'orchestrateur existant).

## Statuts

`pending` | `processing` | `success` | `failed` | `expired` | `refunded`

## Notes

L'orchestrateur Payment IT-Tech est **déjà développé** — ce contrat aligne MHC sur son API existante (phase 4).
