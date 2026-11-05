"""OpenID Connect (OIDC) client helper module.

Implements the Authorization Code Flow manually using requests.
Handles provider metadata discovery, authorization URL generation,
authorization code exchange, and userinfo retrieval.
"""

from typing import Any
import urllib.parse
from django.conf import settings
import requests

# In-memory cache for OIDC provider discovery document
_OIDC_CONFIG_CACHE: dict[str, dict[str, str]] = {}


def get_config(issuer: str | None = None) -> dict[str, str]:
    """Fetch and cache the OpenID Connect discovery document (.well-known/openid-configuration).

    Discovers the provider's authorization, token, and userinfo endpoints.

    Args:
        issuer: Base URL of the OIDC provider. Defaults to settings.OIDC_ISSUER.

    Returns:
        dict: Mapping containing 'authorization_endpoint', 'token_endpoint', and 'userinfo_endpoint'.

    Raises:
        ValueError: If OIDC issuer is not configured.
        requests.RequestException: If discovery endpoint request fails.
    """
    issuer_url = (issuer or getattr(settings, "OIDC_ISSUER", "")).rstrip("/")
    if not issuer_url:
        raise ValueError("OIDC_ISSUER is not configured.")

    if issuer_url in _OIDC_CONFIG_CACHE:
        return _OIDC_CONFIG_CACHE[issuer_url]

    discovery_url = f"{issuer_url}/.well-known/openid-configuration"
    response = requests.get(discovery_url, timeout=10)
    response.raise_for_status()
    data = response.json()

    config = {
        "authorization_endpoint": data["authorization_endpoint"],
        "token_endpoint": data["token_endpoint"],
        "userinfo_endpoint": data["userinfo_endpoint"],
    }
    _OIDC_CONFIG_CACHE[issuer_url] = config
    return config


def clear_config_cache() -> None:
    """Clear cached OIDC discovery configurations (primarily for testing)."""
    _OIDC_CONFIG_CACHE.clear()


def build_authorization_url(state: str) -> str:
    """Construct the OIDC authorization redirect URL with code response type and scopes.

    Redirects the user agent to the provider's login and consent screen.

    Args:
        state: Cryptographically signed state token for CSRF protection.

    Returns:
        str: Fully qualified authorization URL.
    """
    config = get_config()
    auth_endpoint = config["authorization_endpoint"]

    params = {
        "response_type": "code",
        "client_id": getattr(settings, "OIDC_CLIENT_ID", ""),
        "redirect_uri": getattr(settings, "OIDC_REDIRECT_URI", ""),
        "scope": "openid email profile",
        "state": state,
    }
    query = urllib.parse.urlencode(params)
    return f"{auth_endpoint}?{query}"


def exchange_code(code: str) -> str:
    """Exchange the authorization code for an OIDC access token.

    Performs a server-to-server POST to the token endpoint. Never logs the client secret.

    Args:
        code: Authorization code received from the callback query parameter.

    Returns:
        str: Access token string returned by the provider.

    Raises:
        ValueError: If no access token is returned by the provider.
        requests.RequestException: If token endpoint request fails.
    """
    config = get_config()
    token_endpoint = config["token_endpoint"]

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": getattr(settings, "OIDC_CLIENT_ID", ""),
        "client_secret": getattr(settings, "OIDC_CLIENT_SECRET", ""),
        "redirect_uri": getattr(settings, "OIDC_REDIRECT_URI", ""),
    }
    headers = {"Accept": "application/json"}

    response = requests.post(token_endpoint, data=payload, headers=headers, timeout=10)
    response.raise_for_status()
    token_data = response.json()

    access_token = token_data.get("access_token")
    if not access_token:
        raise ValueError("Token response did not contain an access_token.")

    return str(access_token)


def fetch_userinfo(access_token: str) -> dict[str, Any]:
    """Retrieve verified user profile claims from the provider's userinfo endpoint.

    Args:
        access_token: Bearer access token obtained from code exchange.

    Returns:
        dict: Claims including 'email', 'name', 'email_verified', and 'sub'.

    Raises:
        requests.RequestException: If userinfo endpoint request fails.
    """
    config = get_config()
    userinfo_endpoint = config["userinfo_endpoint"]

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    response = requests.get(userinfo_endpoint, headers=headers, timeout=10)
    response.raise_for_status()
    user_data = response.json()

    return {
        "email": user_data.get("email"),
        "name": user_data.get("name", "") or "",
        "email_verified": bool(user_data.get("email_verified", False)),
        "sub": str(user_data.get("sub", "")),
    }

