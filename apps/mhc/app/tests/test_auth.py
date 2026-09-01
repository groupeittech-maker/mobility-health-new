import pytest
from fastapi import status
from app.models.user import User


def _activate_user(db, username: str) -> None:
    u = db.query(User).filter(User.username == username).first()
    assert u is not None
    u.is_active = True
    u.email_verified = True
    db.commit()


def test_register_user(client):
    """Test user registration"""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "testpassword123",
            "full_name": "Test User",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"
    assert "password" not in data


def test_login_user(client, db):
    """Test user login after manual activation (équivalent à verify-email en intégration)."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@example.com",
            "username": "loginuser",
            "password": "loginpassword123",
        },
    )
    _activate_user(db, "loginuser")

    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "loginuser",
            "password": "loginpassword123",
        },
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_get_current_user(client, db):
    """Test getting current user info"""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "me@example.com",
            "username": "meuser",
            "password": "mepassword123",
        },
    )
    _activate_user(db, "meuser")

    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "meuser",
            "password": "mepassword123",
        },
    )
    token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["username"] == "meuser"
