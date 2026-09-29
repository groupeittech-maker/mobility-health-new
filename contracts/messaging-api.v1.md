# Messaging API v1 — contrat public

**Consommateur principal :** MHC (`apps/mhc/app/integrations/messaging/`)

Service de messagerie transactionnelle (SMS / WhatsApp) utilisé pour les codes
de vérification MyMHC : inscription (`canal_verification`), changement d'e-mail
et changement de téléphone.

## Endpoints

### POST /v1/messages/send

Envoie un message transactionnel.

**Request :**
```json
{
  "channel": "sms | whatsapp",
  "to": "+24206XXXXXXX",
  "message": "MyMHC : votre code de vérification est 123456 (valide 15 min).",
  "reference": "verification:42"
}
```

**Response :**
```json
{
  "status": "sent | queued | failed",
  "channel": "sms",
  "message_id": "msg_abc123",
  "details": {}
}
```

**Codes d'erreur :** `400` destination invalide · `429` quota · `5xx` indisponible.
MHC traite `status == "failed"` ou toute erreur HTTP comme un échec d'envoi
(HTTP 503 côté API MyMHC).

## Mode d'activation

`MESSAGING_SERVICE_URL`, `MESSAGING_SERVICE_API_KEY`, `MESSAGING_SERVICE_MODE=live`.
En `stub` (défaut), le client journalise le message et répond `sent`.
