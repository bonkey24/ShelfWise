"""URL routes for authentication endpoints."""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.views import (
    CurrentUserView,
    LoginView,
    RegisterView,
    SSOCallbackView,
    SSOConfigView,
    SSOLoginView,
)

app_name = "accounts"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("me/", CurrentUserView.as_view(), name="auth-me"),
    # OpenID Connect (SSO)
    path("sso/login/", SSOLoginView.as_view(), name="sso-login"),
    path("sso/callback/", SSOCallbackView.as_view(), name="sso-callback"),
    path("sso/config/", SSOConfigView.as_view(), name="sso-config"),
]
