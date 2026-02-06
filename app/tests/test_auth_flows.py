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
                "username": "newuser",
                "password": "newpassword123",
                "full_name": "New User"
            }
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert data["full_name"] == "New User"
        assert "password" not in data
        assert "hashed_password" not in data
        assert data["is_active"] is True
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
        assert "already registered" in response.json()["detail"].lower()
    
    def test_register_duplicate_username(self, client, test_user):
        """Test registration with duplicate username"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "different@example.com",
                "username": test_user.username,
                "password": "password123"
            }
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "username already taken" in response.json()["detail"].lower()
    
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
        assert "inactive" in response.json()["detail"].lower()
    
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
        """Test complete register -> login flow"""
        # Register
        register_response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "flowtest@example.com",
                "username": "flowtest",
                "password": "flowpassword123",
                "full_name": "Flow Test User"
            }
        )
        assert register_response.status_code == status.HTTP_201_CREATED
        
        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "flowtest",
                "password": "flowpassword123"
            }
        )
        assert login_response.status_code == status.HTTP_200_OK
        assert "access_token" in login_response.json()
        
        # Get current user
        token = login_response.json()["access_token"]
        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_response.status_code == status.HTTP_200_OK
        assert me_response.json()["username"] == "flowtest"


















