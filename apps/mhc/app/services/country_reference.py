import time
from typing import List, Dict, Any

from app.services.countries_dev_reference import fetch_countries_from_countries_dev

# Cache mémoire simple (TTL secondes)
_CACHE_TTL = 900  # 15 minutes
_cache_data: List[Dict[str, Any]] | None = None
_cache_expire_at: float = 0


def _now() -> float:
    return time.time()


def _fetch_from_api() -> List[Dict[str, Any]]:
    return fetch_countries_from_countries_dev()


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

