"""Views for authentication endpoints (register, login, refresh, me, and SSO)."""

import secrets
from django.conf import settings
from django.contrib.auth.models import User
from django.core import signing
from django.http import HttpResponseRedirect
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import UserProfile
from apps.accounts.oidc import (
    build_authorization_url,
    exchange_code,
    fetch_userinfo,
)
from apps.accounts.serializers import (
    AuthResponseSerializer,
    LoginSerializer,
    RegisterSerializer,
    SSOConfigSerializer,
    UserSerializer,
)


class RegisterView(APIView):
    """Register a new user account with email and password."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Register user",
        description="Creates a new user account, validates password strength, and returns JWT tokens.",
        request=RegisterSerializer,
        responses={201: AuthResponseSerializer},
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        response_data = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        }
        return Response(response_data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """Authenticate with email and password to receive JWT tokens."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="User login",
        description="Authenticates credentials and returns JWT access/refresh tokens alongside user profile.",
        request=LoginSerializer,
        responses={200: AuthResponseSerializer},
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors or {"detail": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        response_data = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        }
        return Response(response_data, status=status.HTTP_200_OK)


class CurrentUserView(APIView):
    """Retrieve the currently authenticated user's profile."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Current user profile",
        description="Returns the profile (id, email, name, auth_provider) of the authenticated user.",
        responses={200: UserSerializer},
    )
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SSOLoginView(APIView):
    """Initiate OpenID Connect authorization code flow.

    Generates a cryptographically signed state token (with 10-minute validity)
    to protect against CSRF attacks, builds the provider's authorization URL,
    and redirects the user's browser.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="SSO Login Redirect",
        description="Initiates OIDC login flow and redirects to the identity provider.",
        responses={302: None},
    )
    def get(self, request):
        if not (
            getattr(settings, "OIDC_ISSUER", "").strip()
            and getattr(settings, "OIDC_CLIENT_ID", "").strip()
            and getattr(settings, "OIDC_CLIENT_SECRET", "").strip()
            and getattr(settings, "OIDC_REDIRECT_URI", "").strip()
        ):
            return Response(
                {"detail": "SSO is not configured."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 1. Create a random state token and sign it with TimestampSigner (10m TTL)
        random_token = secrets.token_urlsafe(32)
        signer = signing.TimestampSigner(salt="oidc-sso-state")
        signed_state = signer.sign(random_token)

        # 2. Build provider authorization URL and redirect
        try:
            auth_url = build_authorization_url(state=signed_state)
        except Exception as exc:
            return Response(
                {"detail": f"Failed to initialize SSO: {str(exc)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return HttpResponseRedirect(auth_url)


class SSOCallbackView(APIView):
    """Handle OpenID Connect provider callback.

    Validates the CSRF state token, exchanges the authorization code for an access token,
    fetches verified user information, provisions or retrieves the Django user,
    records the 'sso' authentication provider, and issues JWT tokens.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="SSO Callback Handler",
        description="Processes OIDC code exchange, user provisioning, and returns JWT tokens or redirects to frontend.",
        responses={200: AuthResponseSerializer},
    )
    def get(self, request):
        state = request.query_params.get("state")
        code = request.query_params.get("code")

        if not state or not code:
            return Response(
                {"detail": "Missing code or state parameter."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 1. Verify state signature and freshness (max age: 10 minutes = 600s)
        signer = signing.TimestampSigner(salt="oidc-sso-state")
        try:
            signer.unsign(state, max_age=600)
        except (signing.BadSignature, signing.SignatureExpired):
            return Response(
                {"detail": "Invalid or expired state parameter."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 2. Exchange authorization code for OIDC access token
        try:
            access_token = exchange_code(code)
        except Exception as exc:
            return Response(
                {"detail": f"Failed to exchange authorization code: {str(exc)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 3. Retrieve verified user claims from userinfo endpoint
        try:
            userinfo = fetch_userinfo(access_token)
        except Exception as exc:
            return Response(
                {"detail": f"Failed to fetch user profile from provider: {str(exc)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = userinfo.get("email")
        if not email:
            return Response(
                {"detail": "Identity provider did not return an email address."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not userinfo.get("email_verified", False):
            return Response(
                {"detail": "Email address is not verified by identity provider."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 4. Get or provision Django User with unusable password
        email_clean = email.strip().lower()
        name = userinfo.get("name", "").strip()

        user = (
            User.objects.filter(email__iexact=email_clean).first()
            or User.objects.filter(username__iexact=email_clean).first()
        )

        if not user:
            user = User.objects.create_user(
                username=email_clean,
                email=email_clean,
                first_name=name,
            )
            user.set_unusable_password()
            user.save()
        elif name and not user.first_name:
            user.first_name = name
            user.save(update_fields=["first_name"])

        # 5. Record auth_provider as 'sso' in UserProfile
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.auth_provider = "sso"
        profile.save(update_fields=["auth_provider"])
        user.profile = profile

        # 6. Issue ShelfWise SimpleJWT access and refresh tokens
        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)
        refresh_token_str = str(refresh)

        # 7. Redirect to frontend with fragment tokens if FRONTEND_URL configured, otherwise return JSON
        frontend_url = getattr(settings, "FRONTEND_URL", "").strip().rstrip("/")
        if frontend_url:
            redirect_url = f"{frontend_url}/auth/callback#access={access}&refresh={refresh_token_str}"
            return HttpResponseRedirect(redirect_url)

        return Response(
            {
                "access": access,
                "refresh": refresh_token_str,
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class SSOConfigView(APIView):
    """Return SSO configuration status to inform frontend UI display."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="SSO Configuration Status",
        description="Returns whether SSO is enabled based on configured environment variables.",
        responses={200: SSOConfigSerializer},
    )
    def get(self, request):
        enabled = bool(
            getattr(settings, "OIDC_ISSUER", "").strip()
            and getattr(settings, "OIDC_CLIENT_ID", "").strip()
            and getattr(settings, "OIDC_CLIENT_SECRET", "").strip()
            and getattr(settings, "OIDC_REDIRECT_URI", "").strip()
        )
        return Response(
            {
                "enabled": enabled,
                "login_url": "/api/auth/sso/login/",
            },
            status=status.HTTP_200_OK,
        )
