import time
from typing import List, Dict, Any

import httpx

RESTCOUNTRIES_URL = (
    "https://restcountries.com/v3.1/all?"
    "fields=cca2,cca3,name,translations,region,idd,capital"
)

# Cache mémoire simple (TTL secondes)
_CACHE_TTL = 900  # 15 minutes
_cache_data: List[Dict[str, Any]] | None = None
_cache_expire_at: float = 0


def _now() -> float:
    return time.time()


def _fetch_from_api() -> List[Dict[str, Any]]:
    resp = httpx.get(RESTCOUNTRIES_URL, timeout=20.0)
    resp.raise_for_status()
    items = resp.json()

    countries: List[Dict[str, Any]] = []
    for item in items:
        translations = item.get("translations") or {}
        name_fr = (
            translations.get("fra", {}) or {}
        ).get("common") or item.get("name", {}).get("common")
        code = (item.get("cca2") or "").upper().strip()
        if not code or not name_fr:
            continue

        countries.append(
            {
                "code": code,
                "nom": name_fr,
                "region": item.get("region"),
            }
        )

    countries.sort(key=lambda c: c["nom"].lower())
    return countries


def get_reference_countries(force_refresh: bool = False) -> List[Dict[str, Any]]:
    global _cache_data, _cache_expire_at
    if (
        not force_refresh
        and _cache_data is not None
        and _now() < _cache_expire_at
    ):
        return _cache_data

    data = _fetch_from_api()
    _cache_data = data
    _cache_expire_at = _now() + _CACHE_TTL
    return data

