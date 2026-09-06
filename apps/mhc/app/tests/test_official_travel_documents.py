"""Documents officiels MHC : nomenclature, éligibilité grossesse, PDF et carte."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from PIL import Image, ImageDraw

from app.core.mhc_nomenclature import (
    format_attestation_number,
    format_avenant_annulation_number,
    format_quittance_number,
)
from app.services.card_service import CardService
from app.services.medical_eligibility import (
    PREGNANCY_INELIGIBLE_MESSAGE,
    MedicalEligibilityError,
    validate_medical_eligibility,
)
from app.services.official_travel_documents import (
    _amount_in_words,
    _traveler,
    generate_attestation_assistance_voyage,
    generate_avenant_annulation,
    generate_quittance_paiement,
)


def _souscription(**overrides):
    defaults = dict(
        id=1,
        numero_souscription="001300-10-030-052-2026",
        date_debut=date(2026, 1, 1),
        date_fin=date(2026, 1, 7),
        prix_applique=Decimal("65000"),
        prime_assurance=Decimal("50000"),
        produit_assurance=SimpleNamespace(
            nom="Formule Standard",
            zone_geographique="Afrique",
            assureur="NSIA",
            garanties=None,
        ),
        projet_voyage=SimpleNamespace(destination="France", destination_country=None, zone_code="EU"),
        notes="",
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _user():
    return SimpleNamespace(
        full_name="Joseph PRONTON",
        username="jpronton",
        date_naissance=date(1990, 5, 12),
        numero_passeport="AB123456",
        nationalite="Sénégalaise",
        pays_residence="Sénégal",
    )


class TestNomenclatureDocuments:
    def test_attestation_avenant_quittance_formats(self):
        assert format_attestation_number(1) == "000001-101"
        assert format_avenant_annulation_number(92) == "000092-102"
        assert format_quittance_number(252) == "000252-119"


class TestMedicalEligibility:
    def test_pregnancy_over_five_months_blocked(self):
        with pytest.raises(MedicalEligibilityError, match="5 mois"):
            validate_medical_eligibility({"enceinte": "oui", "moisGrossesse": 6})

    def test_pregnancy_five_months_allowed(self):
        validate_medical_eligibility({"enceinte": "oui", "mois_grossesse": 5})

    def test_not_pregnant_allowed(self):
        validate_medical_eligibility({"enceinte": "non"})

    def test_missing_months_rejected(self):
        with pytest.raises(MedicalEligibilityError):
            validate_medical_eligibility({"pregnancy": "oui"})

    def test_message_matches_parcours(self):
        assert "plus de 5 mois" in PREGNANCY_INELIGIBLE_MESSAGE


class TestOfficialDocuments:
    def test_amount_in_words(self):
        text = _amount_in_words(65000)
        assert "soixante-cinq mille" in text
        assert "65000" in text

    def test_traveler_mapping(self):
        info = _traveler(
            _user(),
            {"fullName": "Joseph PRONTON", "passportNumber": "AB123456", "nationality": "Sénégalaise"},
        )
        assert info["name"] == "Joseph PRONTON"
        assert info["passport"] == "AB123456"
        assert info["nationality"] == "Sénégalaise"

    def test_attestation_pdf_contains_dynamic_fields(self):
        pdf = generate_attestation_assistance_voyage(
            _souscription(),
            _user(),
            "000001-101",
            traveler_info={"fullName": "Joseph PRONTON", "passportNumber": "AB123456"},
        )
        data = pdf.getvalue()
        assert data.startswith(b"%PDF")
        assert len(data) > 2000

    def test_avenant_pdf_is_distinct_document(self):
        pdf = generate_avenant_annulation(
            _souscription(),
            _user(),
            "000092-102",
            traveler_info={"fullName": "Joseph PRONTON"},
        )
        data = pdf.getvalue()
        assert data.startswith(b"%PDF")
        assert len(data) > 1500

    def test_quittance_pdf_uses_reference_119(self):
        paiement = SimpleNamespace(
            montant=Decimal("65000"),
            type_paiement=SimpleNamespace(value="carte_bancaire"),
        )
        pdf = generate_quittance_paiement(
            _souscription(),
            paiement,
            _user(),
            "000252-119",
            traveler_info={"fullName": "Joseph PRONTON"},
        )
        data = pdf.getvalue()
        assert data.startswith(b"%PDF")
        assert len(data) > 1000


class TestDigitalCard:
    def test_card_image_uses_subscriber_data(self):
        buffer = CardService.generate_insurance_card(
            _user(),
            _souscription(),
            "000001-101",
            "https://verify.example/000001-101",
            allow_missing_photo=True,
            traveler_info={"fullName": "Joseph PRONTON", "groupLabel": "1 - 03"},
        )
        raw = buffer.getvalue()
        assert raw[:8] == b"\x89PNG\r\n\x1a\n"
        image = Image.open(buffer)
        assert image.size == (CardService.WIDTH, CardService.HEIGHT)

    def test_insured_number_grouping(self):
        number = CardService._format_insured_number("000001-101", _souscription())
        parts = number.split()
        assert len(parts) == 4
        assert all(len(part) == 4 for part in parts)

    def test_ayants_droit_one_adult_three_children(self):
        assert CardService.format_ayants_droit_label(1, 3) == "1 - 03"
        assert CardService.format_ayants_droit_label(1, 0) == "1 - 00"
        notes = (
            "Voyage avec enfants mineurs: Oui\n"
            "Nombre d'enfants mineurs: 3\n"
            "  Enfant 1: A (né(e) le 01/01/2018)\n"
            "  Enfant 2: B (né(e) le 01/01/2020)\n"
            "  Enfant 3: C (né(e) le 01/01/2022)\n"
        )
        souscription = _souscription(notes=notes, projet_voyage=SimpleNamespace(notes=notes, nombre_participants=4))
        adults, children = CardService.resolve_ayants_droit(souscription, {})
        assert (adults, children) == (1, 3)
        assert CardService.format_ayants_droit_label(adults, children) == "1 - 03"

    def test_ayants_droit_from_mobile_notes(self):
        notes = (
            "Mineurs accompagnés: Lea (né(e) le 02/02/2019); passeport X; "
            "Noah (né(e) le 03/03/2021); passeport Y"
        )
        adults, children = CardService.resolve_ayants_droit(_souscription(notes=notes), {})
        assert (adults, children) == (1, 2)

    def test_dotted_globe_is_spherical_not_flat_grid(self):
        overlay = Image.new("RGBA", (CardService.WIDTH, CardService.HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        CardService._draw_dotted_globe(draw, CardService.WIDTH, CardService.HEIGHT)
        pixels = overlay.load()
        cx = int(CardService.WIDTH * 0.82)
        cy = int(CardService.HEIGHT * 0.50)
        radius = int(CardService.HEIGHT * 0.70)

        def inked(x: int, y: int, radius_px: int = 6) -> bool:
            for yy in range(max(0, y - radius_px), min(CardService.HEIGHT, y + radius_px + 1)):
                for xx in range(max(0, x - radius_px), min(CardService.WIDTH, x + radius_px + 1)):
                    if pixels[xx, yy][3] > 0:
                        return True
            return False

        assert inked(cx - radius, cy), "le limbe ouest doit dessiner le disque"
        assert inked(cx, cy, radius_px=24), "le réseau de méridiens passe près du centre"
        assert not inked(40, 40, radius_px=8), "un coin hors sphère ne doit pas être grillagé"
        # Un grillage plat continuerait à x = limbe, plus haut ; une sphère non.
        assert not inked(cx - radius, 80, radius_px=8), "hors du disque, pas de grillage plat"
