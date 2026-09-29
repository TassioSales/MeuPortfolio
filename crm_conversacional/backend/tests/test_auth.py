"""Tests for authentication endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.auth_service import auth_service

client = TestClient(app)


class TestUserRegistration:
    """Test user registration endpoint."""

    def test_register_success(self, sample_user_data):
        """Test successful user registration."""
        response = client.post("/api/v1/auth/register", json=sample_user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == sample_user_data["email"]
        assert data["nome"] == sample_user_data["nome"]
        assert data["status"] == "ativo"
        assert "id" in data
        assert "data_criacao" in data

    def test_register_duplicate_email(self, sample_user_data):
        """Test registration with duplicate email."""
        # First registration
        response1 = client.post("/api/v1/auth/register", json=sample_user_data)
        assert response1.status_code == 201

        # Second registration with same email
        response2 = client.post("/api/v1/auth/register", json=sample_user_data)
        assert response2.status_code == 400
        assert "already exists" in response2.json()["detail"]

    def test_register_missing_email(self, sample_user_data):
        """Test registration with missing email."""
        data = {
            "nome": sample_user_data["nome"],
            "senha": sample_user_data["senha"],
        }
        response = client.post("/api/v1/auth/register", json=data)
        assert response.status_code == 422  # Validation error

    def test_register_missing_senha(self, sample_user_data):
        """Test registration with missing password."""
        data = {
            "email": sample_user_data["email"],
            "nome": sample_user_data["nome"],
        }
        response = client.post("/api/v1/auth/register", json=data)
        assert response.status_code == 422

    def test_register_invalid_email(self):
        """Test registration with invalid email."""
        data = {
            "email": "invalid-email",
            "nome": "Test User",
            "senha": "TestPassword123!",
        }
        response = client.post("/api/v1/auth/register", json=data)
        assert response.status_code == 422


class TestUserLogin:
    """Test user login endpoint."""

    def test_login_success(self, sample_user_data):
        """Test successful login."""
        # Register user first
        client.post("/api/v1/auth/register", json=sample_user_data)

        # Login
        login_data = {
            "email": sample_user_data["email"],
            "senha": sample_user_data["senha"],
        }
        response = client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    def test_login_wrong_password(self, sample_user_data):
        """Test login with wrong password."""
        # Register user first
        client.post("/api/v1/auth/register", json=sample_user_data)

        # Try login with wrong password
        login_data = {
            "email": sample_user_data["email"],
            "senha": "WrongPassword123!",
        }
        response = client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    def test_login_nonexistent_user(self):
        """Test login with nonexistent user."""
        login_data = {
            "email": "nonexistent@example.com",
            "senha": "TestPassword123!",
        }
        response = client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    def test_login_missing_email(self):
        """Test login with missing email."""
        data = {"senha": "TestPassword123!"}
        response = client.post("/api/v1/auth/login", json=data)
        assert response.status_code == 422

    def test_login_missing_password(self):
        """Test login with missing password."""
        data = {"email": "test@example.com"}
        response = client.post("/api/v1/auth/login", json=data)
        assert response.status_code == 422


class TestTokenRefresh:
    """Test token refresh endpoint."""

    def test_refresh_token_success(self, sample_user_data):
        """Test successful token refresh."""
        # Register and login
        client.post("/api/v1/auth/register", json=sample_user_data)
        login_response = client.post("/api/v1/auth/login", json={
            "email": sample_user_data["email"],
            "senha": sample_user_data["senha"],
        })

        refresh_token = login_response.json()["refresh_token"]

        # Refresh token
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    def test_refresh_token_missing(self):
        """Test refresh without token."""
        response = client.post("/api/v1/auth/refresh", json={})
        assert response.status_code == 400

    def test_refresh_token_invalid(self):
        """Test refresh with invalid token."""
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": "invalid-token"
        })
        assert response.status_code == 401


class TestTokenVerification:
    """Test token verification endpoint."""

    def test_verify_token_success(self, sample_user_data):
        """Test successful token verification."""
        # Register and login
        client.post("/api/v1/auth/register", json=sample_user_data)
        login_response = client.post("/api/v1/auth/login", json={
            "email": sample_user_data["email"],
            "senha": sample_user_data["senha"],
        })

        token = login_response.json()["access_token"]

        # Verify token
        response = client.post("/api/v1/auth/verify-token", json={
            "token": token
        })

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert "user_id" in data

    def test_verify_token_invalid(self):
        """Test verification of invalid token."""
        response = client.post("/api/v1/auth/verify-token", json={
            "token": "invalid-token"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False

    def test_verify_token_missing(self):
        """Test verification without token."""
        response = client.post("/api/v1/auth/verify-token", json={})
        assert response.status_code == 400


class TestPasswordHashing:
    """Test password hashing functionality."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "MySecurePassword123!"
        hashed = auth_service.hash_password(password)

        assert hashed != password
        assert len(hashed) > 0

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "MySecurePassword123!"
        hashed = auth_service.hash_password(password)

        assert auth_service.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "MySecurePassword123!"
        hashed = auth_service.hash_password(password)

        assert auth_service.verify_password("WrongPassword", hashed) is False


class TestJWTTokens:
    """Test JWT token creation and verification."""

    def test_create_access_token(self):
        """Test access token creation."""
        user_id = "test-user-123"
        token = auth_service.create_access_token(user_id)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_access_token(self):
        """Test access token verification."""
        user_id = "test-user-123"
        token = auth_service.create_access_token(user_id)
        verified_user_id = auth_service.verify_token(token)

        assert verified_user_id == user_id

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        user_id = "test-user-123"
        token = auth_service.create_refresh_token(user_id)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_refresh_token(self):
        """Test refresh token verification."""
        user_id = "test-user-123"
        token = auth_service.create_refresh_token(user_id)
        new_token = auth_service.refresh_access_token(token)

        assert new_token is not None
        assert isinstance(new_token, str)

    def test_verify_invalid_token(self):
        """Test verification of invalid token."""
        result = auth_service.verify_token("invalid-token")
        assert result is None
