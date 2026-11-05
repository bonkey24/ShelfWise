"""Serializers for authentication and user account management."""

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    """Serializer representing the authenticated user profile."""

    name = serializers.SerializerMethodField()
    auth_provider = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "name", "auth_provider"]

    def get_name(self, obj: User) -> str:
        return obj.first_name or ""

    def get_auth_provider(self, obj: User) -> str:
        profile = getattr(obj, "profile", None)
        if profile and profile.auth_provider:
            return profile.auth_provider
        return "email"


class RegisterSerializer(serializers.Serializer):
    """Serializer for new user registration."""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, min_length=1)
    name = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_email(self, value: str) -> str:
        normalized = value.strip().lower()
        if (
            User.objects.filter(email__iexact=normalized).exists()
            or User.objects.filter(username__iexact=normalized).exists()
        ):
            raise serializers.ValidationError("A user with this email already exists.")
        return normalized

    def validate_password(self, value: str) -> str:
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value

    def create(self, validated_data: dict) -> User:
        email = validated_data["email"]
        password = validated_data["password"]
        name = validated_data.get("name", "").strip()

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name,
        )
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user credential validation."""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs: dict) -> dict:
        email = attrs.get("email", "").strip().lower()
        password = attrs.get("password", "")

        user = (
            User.objects.filter(email__iexact=email).first()
            or User.objects.filter(username__iexact=email).first()
        )

        if not user or not user.check_password(password):
            raise serializers.ValidationError("Invalid email or password.")

        if not user.is_active:
            raise serializers.ValidationError("User account is inactive.")

        attrs["user"] = user
        return attrs


class AuthResponseSerializer(serializers.Serializer):
    """Serializer for JWT token and user profile response."""

    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()


class SSOConfigSerializer(serializers.Serializer):
    """Serializer for SSO availability status."""

    enabled = serializers.BooleanField()
    login_url = serializers.CharField()


