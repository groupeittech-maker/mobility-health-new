"""Tests charte graphique : e-carte, e-mails, constantes brand."""

from io import BytesIO
from unittest.mock import MagicMock, patch

from PIL import Image

from app.core.enums import Role
from app.models.user import User
from app.services.card_service import CardService
from app.services.user_service import UserService


BRAND_PURPLE = "#4e267c"
BRAND_TEAL = "#14AE98"


def _sample_user() -> User:
    """Utilisateur factice (sans persistance DB — évite cycles FK hospitals/users en CI)."""
    return User(
        id=1,
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        role=Role.USER,
        is_active=True,
        email_verified=True,
    )


class TestCardServiceBrand:
    def test_brand_color_constants(self):
        assert CardService.PURPLE_BRAND == BRAND_PURPLE
        assert CardService.TEAL_ACCENT == BRAND_TEAL
        assert CardService.TEXT_ON_LIGHT_TITLE == BRAND_PURPLE
        assert CardService.TEXT_ON_LIGHT_LABEL == BRAND_TEAL

    def test_hex_to_rgb(self):
        assert CardService._hex_to_rgb(BRAND_PURPLE) == (78, 38, 124)
        assert CardService._hex_to_rgb(BRAND_TEAL) == (20, 174, 152)

    def test_card_background_uses_brand_colors(self):
        card = CardService._create_card_background()
        assert card.size == (CardService.WIDTH, CardService.HEIGHT)

        purple_rgb = CardService._hex_to_rgb(BRAND_PURPLE)
        teal_rgb = CardService._hex_to_rgb(BRAND_TEAL)
        pixels = set(card.getdata())

        assert purple_rgb in pixels, "Le violet brand doit apparaître sur la e-carte"
        assert teal_rgb in pixels, "Le teal brand doit apparaître sur la e-carte"
        assert (255, 255, 255) in pixels, "L'en-tête blanc doit être présent"

    def test_card_background_is_valid_png(self):
        card = CardService._create_card_background()
        buffer = BytesIO()
        card.save(buffer, format="PNG")
        buffer.seek(0)
        with Image.open(buffer) as loaded:
            assert loaded.format == "PNG"
            assert loaded.size == (CardService.WIDTH, CardService.HEIGHT)


class TestEmailBrand:
    @patch("app.services.user_service.send_email")
    def test_inscription_approval_email_uses_brand_teal(self, mock_send_email: MagicMock):
        mock_send_email.delay = MagicMock()
        user = _sample_user()

        UserService.send_inscription_approval_email(user)

        mock_send_email.delay.assert_called_once()
        kwargs = mock_send_email.delay.call_args.kwargs
        body_html = kwargs["body_html"]

        assert BRAND_TEAL in body_html
        assert kwargs["to_email"] == user.email
        assert "approuvée" in kwargs["subject"]

    @patch("app.services.user_service.send_email")
    def test_inscription_approval_email_contains_activation_link(self, mock_send_email: MagicMock):
        mock_send_email.delay = MagicMock()
        user = _sample_user()

        UserService.send_inscription_approval_email(user)

        body_html = mock_send_email.delay.call_args.kwargs["body_html"]
        assert "confirm-inscription" in body_html
