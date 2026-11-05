"""Tests for authentication endpoints, registration, login, token refresh, and user profile."""

import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User
from django.core import signing
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import UserProfile
from apps.accounts.oidc import clear_config_cache


@pytest.mark.django_db
class TestAuthEndpoints:
    @pytest.fixture(autouse=True)
    def setup_client(self):
        self.client = APIClient()

    def test_register_success(self):
        """Registering a new valid user returns 201 with tokens and user object."""
        payload = {
            "email": "testregister@shelfwise.app",
            "password": "StrongPassword@123",
            "name": "Test Register",
        }
        resp = self.client.post("/api/auth/register/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()

        assert "access" in data
        assert "refresh" in data
        assert "user" in data
        assert data["user"]["email"] == "testregister@shelfwise.app"
        assert data["user"]["name"] == "Test Register"
        assert data["user"]["auth_provider"] == "email"

        # Check DB persistence
        user = User.objects.get(email="testregister@shelfwise.app")
        assert user.check_password("StrongPassword@123")
        assert user.first_name == "Test Register"

    def test_register_duplicate_email(self):
        """Registering with an already existing email returns 400 Bad Request."""
        User.objects.create_user(
            username="existing@shelfwise.app",
            email="existing@shelfwise.app",
            password="StrongPassword@123",
        )
        payload = {
            "email": "EXISTING@shelfwise.app",  # Case-insensitive duplicate
            "password": "StrongPassword@123",
        }
        resp = self.client.post("/api/auth/register/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        data = resp.json()
        assert "email" in data or "detail" in data

    def test_register_invalid_password(self):
        """Registering with a weak password rejected by Django validators returns 400."""
        payload = {
            "email": "weak@shelfwise.app",
            "password": "123",
        }
        resp = self.client.post("/api/auth/register/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_success(self):
        """Logging in with valid credentials returns 200 with tokens and user profile."""
        User.objects.create_user(
            username="userlogin@shelfwise.app",
            email="userlogin@shelfwise.app",
            password="UserPass@123",
            first_name="Login User",
        )
        payload = {
            "email": "userlogin@shelfwise.app",
            "password": "UserPass@123",
        }
        resp = self.client.post("/api/auth/login/", payload, format="json")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert "access" in data
        assert "refresh" in data
        assert data["user"]["email"] == "userlogin@shelfwise.app"
        assert data["user"]["name"] == "Login User"

    def test_login_failure(self):
        """Logging in with incorrect password or nonexistent email returns 401 Unauthorized."""
        User.objects.create_user(
            username="real@shelfwise.app",
            email="real@shelfwise.app",
            password="RealPassword@123",
        )
        # Incorrect password
        resp_bad_pw = self.client.post(
            "/api/auth/login/",
            {"email": "real@shelfwise.app", "password": "WrongPassword"},
            format="json",
        )
        assert resp_bad_pw.status_code == status.HTTP_401_UNAUTHORIZED

        # Nonexistent user
        resp_bad_user = self.client.post(
            "/api/auth/login/",
            {"email": "nonexistent@shelfwise.app", "password": "AnyPassword"},
            format="json",
        )
        assert resp_bad_user.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_refresh(self):
        """Standard SimpleJWT refresh endpoint returns a fresh access token."""
        user = User.objects.create_user(
            username="refreshuser@shelfwise.app",
            email="refreshuser@shelfwise.app",
            password="Password@123",
        )
        login_resp = self.client.post(
            "/api/auth/login/",
            {"email": "refreshuser@shelfwise.app", "password": "Password@123"},
            format="json",
        )
        refresh_token = login_resp.json()["refresh"]

        refresh_resp = self.client.post(
            "/api/auth/refresh/",
            {"refresh": refresh_token},
            format="json",
        )
        assert refresh_resp.status_code == status.HTTP_200_OK
        assert "access" in refresh_resp.json()

    def test_me_authenticated(self):
        """GET /api/auth/me/ with valid bearer token returns user profile."""
        user = User.objects.create_user(
            username="meuser@shelfwise.app",
            email="meuser@shelfwise.app",
            password="Password@123",
            first_name="Me User",
        )
        login_resp = self.client.post(
            "/api/auth/login/",
            {"email": "meuser@shelfwise.app", "password": "Password@123"},
            format="json",
        )
        access_token = login_resp.json()["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        me_resp = self.client.get("/api/auth/me/")
        assert me_resp.status_code == status.HTTP_200_OK
        data = me_resp.json()
        assert data["email"] == "meuser@shelfwise.app"
        assert data["name"] == "Me User"
        assert data["auth_provider"] == "email"

    def test_me_without_token_returns_401(self):
        """GET /api/auth/me/ without an authentication token returns 401 Unauthorized."""
        resp = self.client.get("/api/auth/me/")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_protected_endpoints_without_token_returns_401(self):
        """Protected endpoints (datasets, forecasts, inventory) require authentication."""
        # Datasets
        resp_datasets = self.client.get("/api/datasets/")
        assert resp_datasets.status_code == status.HTTP_401_UNAUTHORIZED

        # Forecasts
        resp_forecasts = self.client.get("/api/forecasts/")
        assert resp_forecasts.status_code == status.HTTP_401_UNAUTHORIZED

        # Inventory
        resp_inventory = self.client.get("/api/inventory/alerts/")
        assert resp_inventory.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestSSOEndpoints:
    @pytest.fixture(autouse=True)
    def setup_sso(self):
        self.client = APIClient()
        clear_config_cache()
        yield
        clear_config_cache()

    def test_sso_config_reports_disabled_when_env_empty(self, settings):
        """SSO config endpoint returns enabled=False when environment variables are not set."""
        settings.OIDC_ISSUER = ""
        settings.OIDC_CLIENT_ID = ""
        settings.OIDC_CLIENT_SECRET = ""
        settings.OIDC_REDIRECT_URI = ""

        resp = self.client.get("/api/auth/sso/config/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["enabled"] is False
        assert data["login_url"] == "/api/auth/sso/login/"

    def test_sso_config_reports_enabled_when_env_configured(self, settings):
        """SSO config endpoint returns enabled=True when all required OIDC variables are set."""
        settings.OIDC_ISSUER = "https://auth.example.com"
        settings.OIDC_CLIENT_ID = "shelfwise-client"
        settings.OIDC_CLIENT_SECRET = "super-secret"
        settings.OIDC_REDIRECT_URI = "http://localhost:8000/api/auth/sso/callback/"

        resp = self.client.get("/api/auth/sso/config/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["enabled"] is True
        assert data["login_url"] == "/api/auth/sso/login/"

    def test_sso_login_redirect_when_configured(self, settings):
        """GET /api/auth/sso/login/ redirects to OIDC provider with signed state."""
        settings.OIDC_ISSUER = "https://auth.example.com"
        settings.OIDC_CLIENT_ID = "shelfwise-client"
        settings.OIDC_CLIENT_SECRET = "super-secret"
        settings.OIDC_REDIRECT_URI = "http://localhost:8000/api/auth/sso/callback/"

        mock_config = {
            "authorization_endpoint": "https://auth.example.com/oauth2/v1/authorize",
            "token_endpoint": "https://auth.example.com/oauth2/v1/token",
            "userinfo_endpoint": "https://auth.example.com/oauth2/v1/userinfo",
        }
        with patch("apps.accounts.oidc.get_config", return_value=mock_config):
            resp = self.client.get("/api/auth/sso/login/")
            assert resp.status_code == status.HTTP_302_FOUND
            location = resp["Location"]
            assert location.startswith("https://auth.example.com/oauth2/v1/authorize?")
            assert "client_id=shelfwise-client" in location
            assert "response_type=code" in location
            assert "state=" in location

    def test_sso_login_returns_400_when_unconfigured(self, settings):
        """GET /api/auth/sso/login/ returns 400 Bad Request if SSO is not enabled."""
        settings.OIDC_ISSUER = ""
        resp = self.client.get("/api/auth/sso/login/")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_sso_callback_invalid_or_missing_state_returns_400(self):
        """SSO callback rejects invalid, missing, or tampered state tokens."""
        # Missing state
        resp_missing = self.client.get("/api/auth/sso/callback/?code=validcode")
        assert resp_missing.status_code == status.HTTP_400_BAD_REQUEST

        # Tampered state
        resp_tampered = self.client.get("/api/auth/sso/callback/?code=validcode&state=badstate")
        assert resp_tampered.status_code == status.HTTP_400_BAD_REQUEST

    @patch("apps.accounts.views.fetch_userinfo")
    @patch("apps.accounts.views.exchange_code")
    def test_sso_callback_valid_flow_creates_user(
        self, mock_exchange, mock_fetch_userinfo, settings
    ):
        """Valid SSO callback provisions user, assigns 'sso' auth_provider, and returns JWT tokens."""
        settings.FRONTEND_URL = ""
        mock_exchange.return_value = "mock_access_token_123"
        mock_fetch_userinfo.return_value = {
            "email": "new_sso_user@shelfwise.app",
            "name": "Jane Doe",
            "email_verified": True,
            "sub": "oidc-sub-999",
        }

        signer = signing.TimestampSigner(salt="oidc-sso-state")
        valid_state = signer.sign("valid_nonce")

        resp = self.client.get(
            "/api/auth/sso/callback/",
            {"code": "auth_code_xyz", "state": valid_state},
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()

        assert "access" in data
        assert "refresh" in data
        assert data["user"]["email"] == "new_sso_user@shelfwise.app"
        assert data["user"]["name"] == "Jane Doe"
        assert data["user"]["auth_provider"] == "sso"

        # Check User created with unusable password and auth_provider='sso'
        user = User.objects.get(email="new_sso_user@shelfwise.app")
        assert user.has_usable_password() is False
        assert user.first_name == "Jane Doe"
        assert user.profile.auth_provider == "sso"

        # Verify /api/auth/me/ endpoint reflects auth_provider='sso'
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {data['access']}")
        me_resp = self.client.get("/api/auth/me/")
        assert me_resp.status_code == status.HTTP_200_OK
        assert me_resp.json()["auth_provider"] == "sso"

    @patch("apps.accounts.views.fetch_userinfo")
    @patch("apps.accounts.views.exchange_code")
    def test_sso_callback_existing_email_logs_into_same_user(
        self, mock_exchange, mock_fetch_userinfo, settings
    ):
        """Existing user logging in via SSO retains same record and switches auth_provider to 'sso'."""
        settings.FRONTEND_URL = ""
        existing_user = User.objects.create_user(
            username="existing@shelfwise.app",
            email="existing@shelfwise.app",
            password="StrongPassword@123",
            first_name="Original Name",
        )
        assert existing_user.profile.auth_provider == "email"

        mock_exchange.return_value = "mock_access_token_456"
        mock_fetch_userinfo.return_value = {
            "email": "EXISTING@shelfwise.app",  # Case-insensitive match
            "name": "Original Name",
            "email_verified": True,
            "sub": "oidc-sub-existing",
        }

        signer = signing.TimestampSigner(salt="oidc-sso-state")
        valid_state = signer.sign("valid_nonce")

        initial_count = User.objects.count()

        resp = self.client.get(
            "/api/auth/sso/callback/",
            {"code": "auth_code_xyz", "state": valid_state},
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["user"]["email"] == "existing@shelfwise.app"
        assert data["user"]["auth_provider"] == "sso"

        # Ensure no duplicate user was created
        assert User.objects.count() == initial_count

        # Check existing user profile updated to 'sso'
        existing_user.refresh_from_db()
        assert existing_user.profile.auth_provider == "sso"

    @patch("apps.accounts.views.fetch_userinfo")
    @patch("apps.accounts.views.exchange_code")
    def test_sso_callback_unverified_email_rejected(
        self, mock_exchange, mock_fetch_userinfo
    ):
        """Unverified email addresses from OIDC provider are rejected with 400 Bad Request."""
        mock_exchange.return_value = "mock_access_token_789"
        mock_fetch_userinfo.return_value = {
            "email": "unverified@shelfwise.app",
            "name": "Unverified User",
            "email_verified": False,
            "sub": "oidc-sub-unverified",
        }

        signer = signing.TimestampSigner(salt="oidc-sso-state")
        valid_state = signer.sign("valid_nonce")

        resp = self.client.get(
            "/api/auth/sso/callback/",
            {"code": "auth_code_xyz", "state": valid_state},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        data = resp.json()
        assert "not verified" in data["detail"].lower()
        assert not User.objects.filter(email="unverified@shelfwise.app").exists()

    @patch("apps.accounts.views.fetch_userinfo")
    @patch("apps.accounts.views.exchange_code")
    def test_sso_callback_redirects_to_frontend_url(
        self, mock_exchange, mock_fetch_userinfo, settings
    ):
        """When FRONTEND_URL is set, callback redirects to frontend with tokens in hash fragment."""
        settings.FRONTEND_URL = "http://localhost:5173"
        mock_exchange.return_value = "mock_token"
        mock_fetch_userinfo.return_value = {
            "email": "redirect_user@shelfwise.app",
            "name": "Redirect User",
            "email_verified": True,
            "sub": "oidc-sub-redirect",
        }

        signer = signing.TimestampSigner(salt="oidc-sso-state")
        valid_state = signer.sign("valid_nonce")

        resp = self.client.get(
            "/api/auth/sso/callback/",
            {"code": "code123", "state": valid_state},
        )
        assert resp.status_code == status.HTTP_302_FOUND
        location = resp["Location"]
        assert location.startswith("http://localhost:5173/auth/callback#access=")
        assert "&refresh=" in location


class TestOIDCHelper:
    @pytest.fixture(autouse=True)
    def clean_cache(self):
        clear_config_cache()
        yield
        clear_config_cache()

    @patch("apps.accounts.oidc.requests.get")
    def test_get_config_fetches_and_caches(self, mock_get, settings):
        """get_config fetches OIDC discovery JSON and caches it in memory."""
        settings.OIDC_ISSUER = "https://auth.example.com"
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "authorization_endpoint": "https://auth.example.com/oauth2/v1/authorize",
            "token_endpoint": "https://auth.example.com/oauth2/v1/token",
            "userinfo_endpoint": "https://auth.example.com/oauth2/v1/userinfo",
        }
        mock_get.return_value = mock_response

        from apps.accounts.oidc import get_config

        config1 = get_config()
        assert config1["authorization_endpoint"] == "https://auth.example.com/oauth2/v1/authorize"
        assert mock_get.call_count == 1

        # Second call should use cache
        config2 = get_config()
        assert config2 == config1
        assert mock_get.call_count == 1

    @patch("apps.accounts.oidc.get_config")
    def test_build_authorization_url(self, mock_get_config, settings):
        """build_authorization_url formats URL with scopes, state, and credentials."""
        settings.OIDC_CLIENT_ID = "test-client"
        settings.OIDC_REDIRECT_URI = "http://localhost:8000/callback"
        mock_get_config.return_value = {
            "authorization_endpoint": "https://auth.example.com/auth",
            "token_endpoint": "https://auth.example.com/token",
            "userinfo_endpoint": "https://auth.example.com/userinfo",
        }

        from apps.accounts.oidc import build_authorization_url

        url = build_authorization_url(state="signed_state_token")
        assert url.startswith("https://auth.example.com/auth?")
        assert "response_type=code" in url
        assert "client_id=test-client" in url
        assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fcallback" in url
        assert "scope=openid+email+profile" in url
        assert "state=signed_state_token" in url

    @patch("apps.accounts.oidc.requests.post")
    @patch("apps.accounts.oidc.get_config")
    def test_exchange_code(self, mock_get_config, mock_post, settings):
        """exchange_code sends authorization_code grant and returns access token."""
        settings.OIDC_CLIENT_ID = "test-client"
        settings.OIDC_CLIENT_SECRET = "super-secret"
        settings.OIDC_REDIRECT_URI = "http://localhost:8000/callback"
        mock_get_config.return_value = {
            "authorization_endpoint": "https://auth.example.com/auth",
            "token_endpoint": "https://auth.example.com/token",
            "userinfo_endpoint": "https://auth.example.com/userinfo",
        }

        mock_post_resp = MagicMock()
        mock_post_resp.json.return_value = {"access_token": "token_abc123"}
        mock_post.return_value = mock_post_resp

        from apps.accounts.oidc import exchange_code

        token = exchange_code("auth_code_xyz")
        assert token == "token_abc123"
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        assert kwargs["data"]["grant_type"] == "authorization_code"
        assert kwargs["data"]["code"] == "auth_code_xyz"

    @patch("apps.accounts.oidc.requests.get")
    @patch("apps.accounts.oidc.get_config")
    def test_fetch_userinfo(self, mock_get_config, mock_get):
        """fetch_userinfo sends Bearer token and returns standardized user profile claims."""
        mock_get_config.return_value = {
            "authorization_endpoint": "https://auth.example.com/auth",
            "token_endpoint": "https://auth.example.com/token",
            "userinfo_endpoint": "https://auth.example.com/userinfo",
        }

        mock_userinfo_resp = MagicMock()
        mock_userinfo_resp.json.return_value = {
            "email": "user@example.com",
            "name": "Alex Smith",
            "email_verified": True,
            "sub": "sub-12345",
        }
        mock_get.return_value = mock_userinfo_resp

        from apps.accounts.oidc import fetch_userinfo

        info = fetch_userinfo("token_abc123")
        assert info == {
            "email": "user@example.com",
            "name": "Alex Smith",
            "email_verified": True,
            "sub": "sub-12345",
        }
        mock_get.assert_called_once_with(
            "https://auth.example.com/userinfo",
            headers={"Authorization": "Bearer token_abc123", "Accept": "application/json"},
            timeout=10,
        )


