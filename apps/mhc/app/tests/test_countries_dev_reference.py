"""Tests source countries.dev pour la liste mondiale des pays."""
from unittest.mock import patch

from app.services.countries_dev_reference import fetch_countries_from_countries_dev


def test_fetch_countries_from_countries_dev_parses_payload():
    payload = [
        {"alpha2Code": "FR", "name": "France", "region": "Europe"},
        {"alpha2Code": "SN", "name": "Senegal", "region": "Africa"},
    ]

    with patch(
        "app.services.countries_dev_reference.httpx.get",
    ) as mock_get:
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = payload

        countries = fetch_countries_from_countries_dev()

    assert len(countries) == 2
    assert countries[0]["code"] == "FR"
    assert countries[0]["nom"] == "France"
