# Digital Trust API v1 — Identity + Trust

**Consommateur principal :** MHC (`apps/mhc/app/integrations/trust/`)

## Identity (eKYC)

### POST /v1/identity/verify

Vérification d'identité (document + selfie + liveness + OTP).

**Response :**
```json
{
  "session_id": "id_sess_xxx",
  "status": "verified",
  "confidence": 0.95,
  "details": {}
}
```

### POST /v1/otp/send | POST /v1/otp/verify

OTP téléphone / e-mail.

### POST /v1/biometric/verify | POST /v1/liveness/check

Biométrie et détection de vivacité.

## Trust (preuve)

### POST /v1/trust/sign

Signature numérique + horodatage d'un document hashé.

**Request :**
```json
{
  "reference": "ATT-DEF-2026-001",
  "document_hash": "sha256:...",
  "document_type": "attestation",
  "metadata": {}
}
```

**Response :**
```json
{
  "proof_id": "proof_xxx",
  "document_hash": "sha256:...",
  "signature": "...",
  "timestamp": "2026-09-01T10:00:00Z",
  "audit_chain_hash": "..."
}
```

### POST /v1/trust/hash

Calcul hash SHA-256.

### GET /v1/trust/audit/{proof_id}

Consultation chaîne d'audit immuable.

## Séparation conceptuelle

- **Identity** : *Qui est cette personne ?*
- **Trust** : *Comment prouver l'intégrité du document / de l'opération ?*
