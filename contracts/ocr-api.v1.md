# OCR / HTR API v1 — contrat public

**Consommateur principal :** MHC (`apps/mhc/app/integrations/ocr/`)

## Endpoints

### POST /v1/ocr/extract

Extraction de champs depuis un document.

**Request :**
```json
{
  "document_type": "passeport",
  "file_url": "https://...",
  "file_base64": null,
  "filename": "passeport.pdf",
  "language": "fra",
  "metadata": {}
}
```

**Response :**
```json
{
  "fields": {
    "nom": "DUPONT",
    "prenom": "Jean",
    "date_naissance": "1990-01-15",
    "numero_document": "..."
  },
  "confidence": 0.92,
  "raw_text": "...",
  "engine": "paddleocr"
}
```

### POST /v1/ocr/classify (optionnel)

Classification du type de document.

### POST /v1/htr/extract (optionnel)

Reconnaissance manuscrite.

**Mode stub MHC :** délègue à `ia_module` (Tesseract) jusqu'au service externe.
