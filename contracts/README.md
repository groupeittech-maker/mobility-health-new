# Contrats API — plateforme IT-Tech

Contrats publics stables consommés par MHC et les futurs services (Lexia, GEOREF, etc.).

| Service | Fichier | Phase MHC |
|---|---|---|
| Payment Orchestrator | [payment-api.v1.md](./payment-api.v1.md) | 4 — intégration |
| OCR / HTR | [ocr-api.v1.md](./ocr-api.v1.md) | 2 |
| Digital Trust (Identity + Trust) | [trust-api.v1.md](./trust-api.v1.md) | 3 |

Les schémas Pydantic dans `apps/mhc/app/integrations/` implémentent ces contrats côté client MHC.
