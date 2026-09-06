"""Tests endpoint /destinations/reference-countries."""
from unittest.mock import patch

from sqlalchemy.exc import ProgrammingError


def test_reference_countries_returns_db_countries(client, db):
    from app.models.destination import DestinationCountry

    db.add(
        DestinationCountry(
            code="SN",
            nom="Sénégal",
            est_actif=True,
            ordre_affichage=0,
        )
    )
    db.commit()

    response = client.get("/api/v1/destinations/reference-countries?actif_seulement=true")
    assert response.status_code == 200
    payload = response.json()
    assert any(item["code"] == "SN" and item["nom"] == "Sénégal" for item in payload)


def test_reference_countries_falls_back_when_db_schema_mismatch(client):
    err = ProgrammingError(
        "SELECT",
        {},
        Exception('column destination_countries.medecin_conseil_id does not exist'),
    )

    with patch(
        "app.api.v1.destinations._reference_countries_from_db",
        side_effect=err,
    ):
        with patch(
            "app.api.v1.destinations.get_reference_countries",
            return_value=[{"code": "FR", "nom": "France", "region": "Europe"}],
        ) as fallback:
            response = client.get("/api/v1/destinations/reference-countries")

    assert response.status_code == 200
    assert response.json() == [{"code": "FR", "nom": "France", "region": "Europe"}]
    fallback.assert_called_once()
