# IT-TECH eKYC API v1 — Contrat consommé par MHC

**Service :** IT-TECH eKYC — plateforme de confiance numérique (identité, document, biométrie, preuve).

**Consommateur principal :** MHC (`apps/mhc/app/integrations/ekyc/`).

**Principe :** MHC ne pilote pas les étapes de vérification. Il crée une session, reçoit une `verification_url`, et récupère un verdict final via webhook signé et/ou l'API pull.

---

## Auth

### `POST /v1/oauth/token`

OAuth2 `client_credentials`. Le tenant reçoit `client_id` / `client_secret` lors de sa création côté eKYC.

**Request :**
```json
{
  "grant_type": "client_credentials",
  "client_id": "ck_...",
  "client_secret": "cs_..."
}
```

**Response :**
```json
{
  "access_token": "eyJ...",
  "expires_in": 3600,
  "token_type": "bearer"
}
```

---

## Sessions KYC

### `POST /v1/kyc/sessions`

Créer une session pour un assuré.

**Headers :** `Authorization: Bearer <tenant_token>`

**Request :**
```json
{
  "customer_reference": "MHC-USER-12345",
  "flow": "TRAVEL_INSURANCE",
  "metadata": {"subscription_id": "SUB-123"}
}
```

**Response (`201`) :**
```json
{
  "session_id": "KYC-2026-0000A1B2",
  "status": "CREATED",
  "flow": "TRAVEL_INSURANCE",
  "verification_url": "https://ekyc.ittech.cloud/verify/KYC-...?token=...",
  "expires_at": "2026-09-09T12:15:00Z"
}
```

### `GET /v1/kyc/sessions/{session_id}`

Résultat minimisé (statut, checks, identité utile, raisons).

**Response :**
```json
{
  "session_id": "KYC-2026-0000A1B2",
  "customer_reference": "MHC-USER-12345",
  "flow": "TRAVEL_INSURANCE",
  "status": "VERIFIED",
  "checks": {
    "DOCUMENT_VERIFICATION": "PASSED",
    "LIVENESS": "PASSED",
    "FACE_MATCH": "PASSED",
    "OTP": "PASSED"
  },
  "reasons": [],
  "identity": {
    "first_name": "John",
    "last_name": "DOE",
    "date_of_birth": "1990-05-15",
    "nationality": "CIV",
    "document_type": "PASSPORT",
    "document_number": "AB123456",
    "issuing_country": "CIV",
    "expiry_date": "2030-12-31",
    "sex": "M"
  },
  "created_at": "2026-09-09T12:00:00Z",
  "completed_at": "2026-09-09T12:05:00Z"
}
```

**Statuts possibles :** `CREATED`, `IN_PROGRESS`, `PROCESSING`, `VERIFIED`, `REJECTED`, `REVIEW`, `EXPIRED`.

### `POST /v1/kyc/sessions/{session_id}/documents`

Sceller un contrat (attestation, police, avenant) : PDF → SHA-256 → signature → horodatage → archive.

**Request :**
```json
{
  "document_reference": "ATT-DEF-2026-001",
  "title": "Attestation d'assurance",
  "fields": {"assure": "John DOE", "police": "POL-123"},
  "pdf_base64": "JVBERi0x..."  // optionnel
}
```

**Response :**
```json
{
  "signed_document_id": "signed_xxx",
  "session_id": "KYC-2026-0000A1B2",
  "document_reference": "ATT-DEF-2026-001",
  "sha256": "sha256:...",
  "signature_algorithm": "RSASSA-PKCS1-v1_5-SHA256",
  "certificate_fingerprint": "...",
  "timestamp_authority": "local",
  "timestamp_qualified": false,
  "timestamped_at": "2026-09-09T12:10:00Z",
  "download_url": "/v1/kyc/sessions/KYC-.../documents/signed_xxx"
}
```

### `GET /v1/kyc/sessions/{session_id}/documents/{signed_document_id}`

Télécharger le PDF scellé.

---

## Webhooks entrants (MHC reçoit depuis eKYC)

Chaque changement d'état **terminal** déclenche un `POST` vers le `webhook_url` configuré du tenant.

**Headers :**
- `Content-Type: application/json`
- `X-EKYC-Event`: `KYC_VERIFIED`
- `X-EKYC-Timestamp`: `1725871234`
- `X-EKYC-Signature`: `sha256=<hmac>`

**Payload :**
```json
{
  "event": "KYC_VERIFIED",
  "session_id": "KYC-2026-0000A1B2",
  "customer_reference": "MHC-USER-12345",
  "flow": "TRAVEL_INSURANCE",
  "status": "VERIFIED",
  "occurred_at": "2026-09-09T12:05:00Z"
}
```

**Événements :** `KYC_VERIFIED`, `KYC_REJECTED`, `KYC_REVIEW_REQUIRED`, `KYC_EXPIRED`.

**Vérification de signature :**
```
signature = HMAC_SHA256(webhook_secret, timestamp + "." + body)
```
Comparaison en temps constant. Si le webhook est vérifié, MHC répond `200` (sinon eKYC retry).

---

## Flows supportés

| Flow | Documents | Étapes | Échec → REVIEW |
|---|---|---|---|
| `TRAVEL_INSURANCE` | Passeport | DOCUMENT, OCR, DOCUMENT_VERIFICATION, SELFIE, LIVENESS, FACE_MATCH, OTP | `DOCUMENT_VERIFICATION`, `FACE_MATCH` |
| `BANK_ACCOUNT` | CNI, Passeport | idem | `FACE_MATCH` |
| `CITIZEN` | CNI, Titre de séjour | DOCUMENT, OCR, DOCUMENT_VERIFICATION, OTP | `DOCUMENT_VERIFICATION` |

**Règles :**
- Liveness échoué = **REJECTED** (bloquant).
- Face match échoué = **REVIEW** (sauf flow CITIZEN qui n'a pas de face match).
- Document périmé ou non authentique = **REJECTED**.
- Confiance documentaire basse = **REVIEW**.

---

## Minimisation des données

- Le tenant reçoit : statut, checks métier, identité utile, `session_id`, `customer_reference`.
- Les images, selfies, scores bruts et payloads fournisseurs restent dans eKYC.
- L'identité complète (`document_number`, etc.) n'est transmise que pour les statuts `VERIFIED` et `REVIEW`.

---

## Sécurité

- Authentification par OAuth2 `client_credentials` côté API.
- Jeton de session à usage unique et limité à une session pour l'UI hébergée.
- Webhooks signés par HMAC.
- Chaîne d'audit hachée, vérifiable via `GET /v1/kyc/sessions/{id}/audit`.
- Stockage objet namespacé par tenant.
