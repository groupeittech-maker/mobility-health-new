"""Source de secours pour la liste mondiale des pays (RestCountries v3.1 est déprécié)."""
from __future__ import annotations

from typing import Any

import httpx

COUNTRIES_DEV_URL = "https://countries.dev/countries?limit=300"


def fetch_countries_from_countries_dev() -> list[dict[str, Any]]:
    response = httpx.get(COUNTRIES_DEV_URL, timeout=30.0, follow_redirects=True)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError("Format inattendu pour countries.dev")

    countries: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        code = (item.get("alpha2Code") or "").strip().upper()
        nom = (item.get("name") or "").strip()
        region = item.get("region")
        if not code or not nom:
            continue
        countries.append({"code": code, "nom": nom, "region": region})

    countries.sort(key=lambda entry: entry["nom"].lower())
    return countries
