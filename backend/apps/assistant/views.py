"""Views for the ShelfWise Assistant conversational API."""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers

from apps.assistant.services import generate_assistant_response


class AssistantUserRateThrottle(UserRateThrottle):
    """Throttle requests to 20 requests per minute per authenticated user."""
    rate = "20/min"


class AssistantChatView(APIView):
    """Conversational intelligence endpoint grounded in real forecasting and inventory data."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [AssistantUserRateThrottle]

    @extend_schema(
        summary="Chat with ShelfWise AI Assistant",
        description=(
            "Accepts a multi-turn conversation and returns a response generated using "
            "native tool calling or grounded offline rules."
        ),
        request=inline_serializer(
            name="AssistantChatRequest",
            fields={
                "messages": serializers.ListField(
                    child=serializers.DictField(),
                    help_text="List of message objects with 'role' and 'content'. Max 20 messages.",
                )
            },
        ),
        responses={
            200: inline_serializer(
                name="AssistantChatResponse",
                fields={
                    "reply": serializers.CharField(),
                    "tools_used": serializers.ListField(child=serializers.CharField()),
                },
            ),
            400: inline_serializer(
                name="AssistantChatError",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def post(self, request):
        messages = request.data.get("messages")

        # Validation: non-empty list
        if not isinstance(messages, list) or len(messages) == 0:
            return Response(
                {"error": "Field 'messages' must be a non-empty list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validation: max 20 messages
        if len(messages) > 20:
            return Response(
                {"error": "Exceeded maximum limit of 20 messages."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validation: message shape and content limit
        validated_messages = []
        for idx, msg in enumerate(messages):
            if not isinstance(msg, dict):
                return Response(
                    {"error": f"Message at index {idx} must be a JSON object."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            role = msg.get("role")
            content = msg.get("content")

            if role not in ("user", "assistant"):
                return Response(
                    {"error": f"Message at index {idx} has invalid role '{role}'. Allowed: 'user', 'assistant'."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not isinstance(content, str) or not content.strip():
                return Response(
                    {"error": f"Message at index {idx} must have non-empty string content."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if len(content) > 2000:
                return Response(
                    {"error": f"Message at index {idx} exceeds 2000 character limit ({len(content)} chars)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            validated_messages.append({"role": role, "content": content.strip()})

        # Generate grounded response
        result = generate_assistant_response(validated_messages)
        return Response(result, status=status.HTTP_200_OK)

