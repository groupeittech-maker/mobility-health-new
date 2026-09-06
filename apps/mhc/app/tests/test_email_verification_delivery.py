"""Envoi e-mail : vérification inscription en SMTP synchrone."""
from unittest.mock import MagicMock, patch

import pytest

from app.services.email_delivery import EmailDeliveryError, dispatch_email
from app.services.user_service import UserService
from app.models.user import User
from app.core.enums import Role


def _user() -> User:
    return User(
        id=42,
        email="test@example.com",
        username="test@example.com",
        full_name="Test User",
        role=Role.USER,
        is_active=False,
    )


class TestVerificationEmailDelivery:
    @patch("app.services.user_service.dispatch_email")
    def test_verification_email_sent_synchronously(self, mock_dispatch: MagicMock):
        UserService.send_verification_email(_user(), "123456")
        mock_dispatch.assert_called_once()
        kwargs = mock_dispatch.call_args.kwargs
        assert kwargs["to_email"] == "test@example.com"
        assert kwargs["synchronous"] is True
        assert "123456" in kwargs["body_html"]
        assert "123456" in kwargs["body_text"]

    @patch("app.services.email_delivery.deliver_email_sync")
    def test_dispatch_email_sync_mode(self, mock_sync: MagicMock):
        mock_sync.return_value = {"status": "success"}
        result = dispatch_email(
            to_email="a@b.com",
            subject="Test",
            body_html="<p>Hi</p>",
            body_text="Hi",
            synchronous=True,
        )
        assert result["status"] == "success"
        mock_sync.assert_called_once()

    @patch("app.services.user_service.dispatch_email")
    def test_verification_email_propagates_smtp_error(self, mock_dispatch: MagicMock):
        mock_dispatch.side_effect = EmailDeliveryError("SMTP down")
        with pytest.raises(EmailDeliveryError):
            UserService.send_verification_email(_user(), "654321")
