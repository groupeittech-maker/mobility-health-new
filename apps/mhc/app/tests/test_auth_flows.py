"""
Comprehensive authentication flow tests
"""
import pytest
from fastapi import status


@pytest.mark.auth
class TestAuthFlows:
    """Test authentication flows"""
    
    def test_register_new_user(self, client, db):
        """Test user registration"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "newpassword123",
                "full_name": "New User"
            }
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert "password" not in data
        assert "hashed_password" not in data
        assert data["is_active"] is False
        assert data.get("email_verified") is False
        assert data["role"] == "user"
    
    def test_register_duplicate_email(self, client, test_user):
        """Test registration with duplicate email"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "username": "differentuser",
                "password": "password123"
            }
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        detail = response.json()["detail"].lower()
        assert "déjà" in detail or "already" in detail
    
    def test_register_duplicate_username_uses_email(self, client, test_user):
        """Le nom d'utilisateur est toujours l'e-mail : doublon = e-mail déjà pris."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "password": "password123"
            }
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        detail = response.json()["detail"].lower()
        assert "déjà" in detail or "already" in detail
    
    def test_register_invalid_email(self, client):
        """Test registration with invalid email"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email",
                "username": "testuser",
                "password": "password123"
            }
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_login_success(self, client, test_user):
        """Test successful login"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.username,
                "password": "testpassword123"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0
        assert len(data["refresh_token"]) > 0
    
    def test_login_wrong_password(self, client, test_user):
        """Test login with wrong password"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.username,
                "password": "wrongpassword"
            }
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "incorrect" in response.json()["detail"].lower()
    
    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent",
                "password": "password123"
            }
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_login_inactive_user(self, client, db):
        """Test login with inactive user"""
        from app.models.user import User
        from app.core.security import get_password_hash
        
        inactive_user = User(
            email="inactive@example.com",
            username="inactive",
            hashed_password=get_password_hash("password123"),
            is_active=False
        )
        db.add(inactive_user)
        db.commit()
        
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "inactive",
                "password": "password123"
            }
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        detail = response.json()["detail"].lower()
        assert "vérification" in detail or "code" in detail or "e-mail" in detail or "email" in detail
    
    def test_get_current_user(self, client, auth_headers):
        """Test getting current user info"""
        response = client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert "username" in data
        assert "is_active" in data
        assert "role" in data
    
    def test_get_current_user_unauthorized(self, client):
        """Test getting current user without token"""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_refresh_token_success(self, client, test_user):
        """Test successful token refresh"""
        # First login
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.username,
                "password": "testpassword123"
            }
        )
        refresh_token = login_response.json()["refresh_token"]
        
        # Refresh token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        # New tokens should be different
        assert data["refresh_token"] != refresh_token
    
    def test_refresh_token_invalid(self, client):
        """Test refresh with invalid token"""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_refresh_token"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_refresh_token_access_token(self, client, test_user):
        """Test refresh with access token (should fail)"""
        # First login
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.username,
                "password": "testpassword123"
            }
        )
        access_token = login_response.json()["access_token"]
        
        # Try to refresh with access token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_logout_success(self, client, auth_headers, test_user):
        """Test successful logout"""
        response = client.post(
            "/api/v1/auth/logout",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        assert "successfully" in response.json()["message"].lower()
        
        # Verify token is invalidated by trying to use it
        # Note: This depends on Redis implementation
        # For now, we just check the logout endpoint works
    
    def test_logout_unauthorized(self, client):
        """Test logout without token"""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_token_expiration(self, client, test_user):
        """Test that expired tokens are rejected"""
        # This test would require mocking time or using very short expiration
        # For now, we'll test that tokens are required
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer expired_token_here"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_register_and_login_flow(self, client, db):
        """Test complete register -> activate -> login flow"""
        register_response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "flowtest@example.com",
                "password": "flowpassword123",
                "full_name": "Flow Test User"
            }
        )
        assert register_response.status_code == status.HTTP_201_CREATED

        from app.models.user import User

        u = db.query(User).filter(User.username == "flowtest@example.com").first()
        assert u is not None
        u.is_active = True
        u.email_verified = True
        db.commit()

        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "flowtest@example.com",
                "password": "flowpassword123"
            }
        )
        assert login_response.status_code == status.HTTP_200_OK
        assert "access_token" in login_response.json()

        token = login_response.json()["access_token"]
        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_response.status_code == status.HTTP_200_OK
        assert me_response.json()["username"] == "flowtest@example.com"

    def test_login_auto_activates_verified_approved_user(self, client, db):
        """Compte e-mail vérifié et approuvé mais inactif : connexion autorisée."""
        from app.models.user import User
        from app.core.security import get_password_hash

        user = User(
            email="verified@example.com",
            username="verified@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=False,
            email_verified=True,
            validation_inscription="approved",
        )
        db.add(user)
        db.commit()

        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "verified@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        db.refresh(user)
        assert user.is_active is True

    def test_admin_login_with_username(self, client, test_admin):
        """Les administrateurs se connectent avec leur nom d'utilisateur, pas l'e-mail."""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_admin.username,
                "password": "adminpassword123",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.json()

    def test_admin_inactive_not_prompted_for_email_otp(self, client, db):
        """Un compte admin inactif ne doit pas être bloqué par le flux OTP voyageur."""
        from app.models.user import User
        from app.core.security import get_password_hash
        from app.core.enums import Role

        admin = User(
            email="inactive.admin@example.com",
            username="inactive_admin",
            hashed_password=get_password_hash("adminpassword123"),
            full_name="Inactive Admin",
            role=Role.ADMIN,
            is_active=False,
            email_verified=False,
            validation_inscription="approved",
        )
        db.add(admin)
        db.commit()

        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "inactive_admin",
                "password": "adminpassword123",
            },
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "code de vérification" not in response.json()["detail"].lower()

















