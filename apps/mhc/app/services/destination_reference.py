import logging
import time
import unicodedata
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.models.destination import DestinationCity, DestinationCountry

logger = logging.getLogger(__name__)

RESTCOUNTRIES_URL = (
    "https://restcountries.com/v3.1/all?"
    "fields=cca2,name,translations,capital,altSpellings"
)
COUNTRIESNOW_URL = "https://countriesnow.space/api/v0.1/countries"

_CACHE_TTL_SECONDS = 24 * 60 * 60
_reference_cache: list[dict[str, Any]] | None = None
_reference_cache_expire_at = 0.0

_COUNTRY_ALIASES = {
    "ivorycoast": "cotedivoire",
    "cotedivoire": "cotedivoire",
    "drcongo": "democraticrepublicofthecongo",
    "democraticrepublicofcongo": "democraticrepublicofthecongo",
    "congodemocraticrepublic": "democraticrepublicofthecongo",
    "republicofcongo": "congo",
    "capeverde": "caboverde",
    "czechrepublic": "czechia",
    "swaziland": "eswatini",
    "southkorea": "korea",
    "northkorea": "koreademocraticpeoplesrepublicof",
    "russia": "russianfederation",
    "syria": "syrianarabrepublic",
    "laos": "laopeoplesdemocraticrepublic",
    "moldova": "moldovarepublicof",
    "bolivia": "boliviaplurinationalstateof",
    "venezuela": "venezuelabolivarianrepublicof",
    "tanzania": "tanzaniaunitedrepublicof",
    "palestine": "palestinestateof",
    "micronesia": "micronesiafederatedstatesof",
    "brunei": "bruneidarussalam",
    "iran": "iranislamicrepublicof",
}


def _now() -> float:
    return time.time()


def _normalize_name(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFD", value.lower().strip())
    normalized = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    normalized = "".join(char for char in normalized if char.isalnum())
    return _COUNTRY_ALIASES.get(normalized, normalized)


def _title_case_cities(cities: list[str], capital: str | None) -> list[str]:
    dedup: list[str] = []
    seen: set[str] = set()

    def _push(name: str | None) -> None:
        city = (name or "").strip()
        if not city:
            return
        key = _normalize_name(city)
        if not key or key in seen:
            return
        seen.add(key)
        dedup.append(city)

    _push(capital)
    for city in cities:
        _push(city)
    return dedup


def _extract_rest_countries() -> list[dict[str, Any]]:
    response = httpx.get(RESTCOUNTRIES_URL, timeout=60.0)
    response.raise_for_status()
    payload = response.json()

    countries: list[dict[str, Any]] = []
    for item in payload:
        code = (item.get("cca2") or "").upper().strip()
        name = (item.get("translations", {}).get("fra", {}) or {}).get("common")
        if not name:
            name = item.get("name", {}).get("common")
        if not code or not name:
            continue

        aliases = {
            _normalize_name(name),
            _normalize_name(item.get("name", {}).get("common")),
            _normalize_name(item.get("name", {}).get("official")),
        }
        for alt in item.get("altSpellings") or []:
            aliases.add(_normalize_name(alt))
        for translation in (item.get("translations") or {}).values():
            if isinstance(translation, dict):
                aliases.add(_normalize_name(translation.get("common")))
                aliases.add(_normalize_name(translation.get("official")))

        capital_list = item.get("capital") or []
        capital = capital_list[0].strip() if capital_list else None

        countries.append(
            {
                "code": code,
                "nom": name.strip(),
                "capital": capital,
                "aliases": {alias for alias in aliases if alias},
            }
        )

    countries.sort(key=lambda entry: entry["nom"].lower())
    return countries


def _extract_country_now_cities() -> dict[str, list[str]]:
    response = httpx.get(COUNTRIESNOW_URL, timeout=120.0)
    response.raise_for_status()
    payload = response.json()

    data = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(data, list):
        raise ValueError("Format inattendu pour la liste des pays/villes")

    result: dict[str, list[str]] = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        country_name = item.get("country")
        cities = item.get("cities")
        if not isinstance(country_name, str) or not isinstance(cities, list):
            continue
        result[_normalize_name(country_name)] = [
            city.strip()
            for city in cities
            if isinstance(city, str) and city.strip()
        ]
    return result


def get_world_destination_reference(
    force_refresh: bool = False,
    max_cities_per_country: int = 40,
) -> list[dict[str, Any]]:
    global _reference_cache, _reference_cache_expire_at

    if (
        not force_refresh
        and _reference_cache is not None
        and _now() < _reference_cache_expire_at
    ):
        return _reference_cache

    rest_countries = _extract_rest_countries()
    try:
        countries_now = _extract_country_now_cities()
    except Exception as exc:
        logger.warning(
            "Impossible de recuperer les villes via CountriesNow, fallback capitals only: %s",
            exc,
        )
        countries_now = {}

    merged: list[dict[str, Any]] = []
    for index, country in enumerate(rest_countries, start=1):
        matched_cities: list[str] = []
        for alias in country["aliases"]:
            if alias in countries_now:
                matched_cities = countries_now[alias]
                break

        ordered_cities = _title_case_cities(matched_cities, country.get("capital"))
        if max_cities_per_country > 0:
            ordered_cities = ordered_cities[:max_cities_per_country]

        merged.append(
            {
                "code": country["code"],
                "nom": country["nom"],
                "ordre_affichage": index,
                "villes": ordered_cities,
            }
        )

    _reference_cache = merged
    _reference_cache_expire_at = _now() + _CACHE_TTL_SECONDS
    return merged


def sync_destination_reference_to_db(
    db: Session,
    force_refresh: bool = False,
    max_cities_per_country: int = 40,
) -> dict[str, int]:
    reference = get_world_destination_reference(
        force_refresh=force_refresh,
        max_cities_per_country=max_cities_per_country,
    )

    existing_countries = {
        country.code.upper(): country
        for country in db.query(DestinationCountry).all()
    }

    countries_created = 0
    countries_updated = 0
    cities_created = 0
    cities_updated = 0

    for country_data in reference:
        code = country_data["code"].upper()
        country = existing_countries.get(code)
        if country is None:
            country = DestinationCountry(
                code=code,
                nom=country_data["nom"],
                est_actif=True,
                ordre_affichage=country_data["ordre_affichage"],
            )
            db.add(country)
            db.flush()
            existing_countries[code] = country
            countries_created += 1
        else:
            changed = False
            if country.nom != country_data["nom"]:
                country.nom = country_data["nom"]
                changed = True
            if country.ordre_affichage != country_data["ordre_affichage"]:
                country.ordre_affichage = country_data["ordre_affichage"]
                changed = True
            if not country.est_actif:
                country.est_actif = True
                changed = True
            if changed:
                countries_updated += 1

        existing_cities = {
            _normalize_name(city.nom): city
            for city in db.query(DestinationCity)
            .filter(DestinationCity.pays_id == country.id)
            .all()
        }

        for index, city_name in enumerate(country_data["villes"], start=1):
            city_key = _normalize_name(city_name)
            city = existing_cities.get(city_key)
            if city is None:
                db.add(
                    DestinationCity(
                        pays_id=country.id,
                        nom=city_name,
                        est_actif=True,
                        ordre_affichage=index,
                    )
                )
                cities_created += 1
            else:
                changed = False
                if city.nom != city_name:
                    city.nom = city_name
                    changed = True
                if city.ordre_affichage != index:
                    city.ordre_affichage = index
                    changed = True
                if not city.est_actif:
                    city.est_actif = True
                    changed = True
                if changed:
                    cities_updated += 1

    db.commit()

    stats = {
        "countries_created": countries_created,
        "countries_updated": countries_updated,
        "cities_created": cities_created,
        "cities_updated": cities_updated,
        "countries_total": len(reference),
    }
    logger.info("Synchronisation destinations terminée: %s", stats)
    return stats
