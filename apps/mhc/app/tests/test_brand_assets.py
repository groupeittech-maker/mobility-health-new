"""Tests charte graphique : e-carte, e-mails, constantes brand."""

import os
from io import BytesIO
from unittest.mock import MagicMock, patch

from PIL import Image, ImageOps

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

    def test_card_background_uses_official_asset(self):
        card = CardService._create_card_background()
        assert card.size == (CardService.WIDTH, CardService.HEIGHT)
        assert os.path.isfile(CardService.CARD_BACKGROUND_PATH)

        resample = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS
        with Image.open(CardService.CARD_BACKGROUND_PATH) as source:
            expected = ImageOps.fit(source.convert("RGB"), card.size, method=resample)
        for point in ((40, 300), (500, 300), (900, 300)):
            assert card.getpixel(point) == expected.getpixel(point)

    def test_card_background_is_valid_png(self):
        card = CardService._create_card_background()
        buffer = BytesIO()
        card.save(buffer, format="PNG")
        buffer.seek(0)
        with Image.open(buffer) as loaded:
            assert loaded.format == "PNG"
            assert loaded.size == (CardService.WIDTH, CardService.HEIGHT)


class TestEmailBrand:
    @patch("app.services.user_service.dispatch_email")
    def test_inscription_approval_email_uses_brand_teal(self, mock_dispatch: MagicMock):
        user = _sample_user()

        UserService.send_inscription_approval_email(user)

        mock_dispatch.assert_called_once()
        kwargs = mock_dispatch.call_args.kwargs
        body_html = kwargs["body_html"]

        assert BRAND_TEAL in body_html
        assert kwargs["to_email"] == user.email
        assert "approuvée" in kwargs["subject"]

    @patch("app.services.user_service.dispatch_email")
    def test_inscription_approval_email_contains_activation_link(self, mock_dispatch: MagicMock):
        user = _sample_user()

        UserService.send_inscription_approval_email(user)

        body_html = mock_dispatch.call_args.kwargs["body_html"]
        assert "confirm-inscription" in body_html
