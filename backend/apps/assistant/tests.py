"""Tests for Assistant app endpoints, providers, and tools."""

from unittest.mock import MagicMock, patch
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.forecasts.models import ForecastRun
from apps.inventory.models import StockLevel
from apps.retail.models import Product, Store

User = get_user_model()


@pytest.fixture
def auth_client():
    user = User.objects.create_user(username="assist_test@shelfwise.app", password="password123")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def sample_retail_setup(db):
    store = Store.objects.create(code="S1097", name="Store 1097")
    product = Product.objects.create(sku="P1", name="Product 1")
    StockLevel.objects.create(store=store, product=product, on_hand=150.0, lead_time_days=7)
    run = ForecastRun.objects.create(
        status="done",
        metrics={
            "Naive": {"WAPE": 0.23, "Bias": 0.1, "RMSSE": 0.35},
            "Seasonal Naive (28d)": {"WAPE": 0.11, "Bias": 0.02, "RMSSE": 0.20},
            "LightGBM": {"WAPE": 0.088, "Bias": -0.01, "RMSSE": 0.16},
        },
    )
    return store, product, run


@pytest.mark.django_db
class TestAssistantChatEndpoint:
    def test_unauthenticated_returns_401(self):
        client = APIClient()
        resp = client.post(
            "/api/assistant/chat/",
            {"messages": [{"role": "user", "content": "hi"}]},
            format="json",
        )
        assert resp.status_code == 401

    def test_empty_or_invalid_messages_rejected(self, auth_client):
        # Empty list
        resp = auth_client.post("/api/assistant/chat/", {"messages": []}, format="json")
        assert resp.status_code == 400

        # Non-list
        resp = auth_client.post("/api/assistant/chat/", {"messages": "hello"}, format="json")
        assert resp.status_code == 400

        # Invalid role
        resp = auth_client.post(
            "/api/assistant/chat/",
            {"messages": [{"role": "system", "content": "hello"}]},
            format="json",
        )
        assert resp.status_code == 400

        # Missing content
        resp = auth_client.post(
            "/api/assistant/chat/",
            {"messages": [{"role": "user", "content": ""}]},
            format="json",
        )
        assert resp.status_code == 400

    def test_oversized_input_rejected(self, auth_client):
        # More than 20 messages
        messages_21 = [{"role": "user", "content": f"msg {i}"} for i in range(21)]
        resp = auth_client.post("/api/assistant/chat/", {"messages": messages_21}, format="json")
        assert resp.status_code == 400
        assert "20 messages" in resp.data["error"]

        # Content exceeds 2000 characters
        long_content = "a" * 2001
        resp = auth_client.post(
            "/api/assistant/chat/",
            {"messages": [{"role": "user", "content": long_content}]},
            format="json",
        )
        assert resp.status_code == 400
        assert "2000 character limit" in resp.data["error"]

    def test_offline_fallback_stockout_risks(self, auth_client, sample_retail_setup, settings):
        settings.LLM_PROVIDER = "none"
        resp = auth_client.post(
            "/api/assistant/chat/",
            {"messages": [{"role": "user", "content": "Which items will stock out soon?"}]},
            format="json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "(offline mode)" in data["reply"]
        assert "get_inventory_summary" in data["tools_used"]
        assert "get_alerts" in data["tools_used"]

    def test_offline_fallback_reorder(self, auth_client, sample_retail_setup, settings):
        settings.LLM_PROVIDER = "none"
        resp = auth_client.post(
            "/api/assistant/chat/",
            {"messages": [{"role": "user", "content": "What should I reorder this week?"}]},
            format="json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "(offline mode)" in data["reply"]
        assert "get_alerts" in data["tools_used"]

    def test_offline_fallback_forecast_accuracy(self, auth_client, sample_retail_setup, settings):
        settings.LLM_PROVIDER = "none"
        resp = auth_client.post(
            "/api/assistant/chat/",
            {"messages": [{"role": "user", "content": "How accurate is the forecast?"}]},
            format="json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "(offline mode)" in data["reply"]
        assert "get_model_metrics" in data["tools_used"]
        assert "LightGBM" in data["reply"]

    @patch("apps.assistant.providers.requests.post")
    def test_mocked_anthropic_tool_call(self, mock_post, auth_client, settings, sample_retail_setup):
        settings.LLM_PROVIDER = "anthropic"
        settings.LLM_API_KEY = "test-anthropic-key"
        settings.LLM_MODEL = "claude-3-5-sonnet-20241022"

        # Turn 1: Claude asks to call get_model_metrics
        resp1 = MagicMock()
        resp1.status_code = 200
        resp1.json.return_value = {
            "stop_reason": "tool_use",
            "content": [
                {
                    "type": "tool_use",
                    "id": "tool_call_1",
                    "name": "get_model_metrics",
                    "input": {},
                }
            ],
        }

        # Turn 2: Claude produces final grounded response
        resp2 = MagicMock()
        resp2.status_code = 200
        resp2.json.return_value = {
            "stop_reason": "end_turn",
            "content": [
                {
                    "type": "text",
                    "text": "The LightGBM model has a WAPE of 8.8%, outperforming the 11.0% Seasonal Naive baseline.",
                }
            ],
        }

        mock_post.side_effect = [resp1, resp2]

        resp = auth_client.post(
            "/api/assistant/chat/",
            {"messages": [{"role": "user", "content": "Give me the WAPE metrics."}]},
            format="json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "get_model_metrics" in data["tools_used"]
        assert "The LightGBM model has a WAPE of 8.8%" in data["reply"]
        assert "(offline mode)" not in data["reply"]

    @patch("apps.assistant.providers.requests.post")
    def test_mocked_gemini_tool_call(self, mock_post, auth_client, settings, sample_retail_setup):
        settings.LLM_PROVIDER = "gemini"
        settings.LLM_API_KEY = "test-gemini-key"
        settings.LLM_MODEL = "gemini-2.0-flash"

        # Turn 1: Gemini calls function
        resp1 = MagicMock()
        resp1.status_code = 200
        resp1.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "functionCall": {
                                    "name": "get_inventory_summary",
                                    "args": {},
                                }
                            }
                        ]
                    }
                }
            ]
        }

        # Turn 2: Gemini returns grounded answer
        resp2 = MagicMock()
        resp2.status_code = 200
        resp2.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": "There are currently 0 stockout risks in your catalog.",
                            }
                        ]
                    }
                }
            ]
        }

        mock_post.side_effect = [resp1, resp2]

        resp = auth_client.post(
            "/api/assistant/chat/",
            {"messages": [{"role": "user", "content": "How many items are stockout risks?"}]},
            format="json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "get_inventory_summary" in data["tools_used"]
        assert "There are currently 0 stockout risks" in data["reply"]
        assert "(offline mode)" not in data["reply"]

    def test_rate_limit_throttle(self, auth_client, sample_retail_setup, settings):
        settings.LLM_PROVIDER = "none"
        from django.core.cache import cache
        cache.clear()

        # Execute 20 allowed requests
        for _ in range(20):
            r = auth_client.post(
                "/api/assistant/chat/",
                {"messages": [{"role": "user", "content": "How accurate is the forecast?"}]},
                format="json",
            )
            assert r.status_code == 200

        # 21st request is throttled
        r21 = auth_client.post(
            "/api/assistant/chat/",
            {"messages": [{"role": "user", "content": "How accurate is the forecast?"}]},
            format="json",
        )
        assert r21.status_code == 429

    @patch("apps.assistant.providers.time.sleep")
    @patch("apps.assistant.providers.requests.post")
    def test_mocked_429_then_success(self, mock_post, mock_sleep, auth_client, settings, sample_retail_setup):
        settings.LLM_PROVIDER = "gemini"
        settings.LLM_API_KEY = "test-gemini-key"
        settings.LLM_MODEL = "gemini-3.5-flash"

        # 1st call returns 429 with Retry-After header
        resp1 = MagicMock()
        resp1.status_code = 429
        resp1.headers = {"Retry-After": "14"}
        resp1.text = '{"error": {"code": 429, "message": "Quota exceeded"}}'
        resp1.json.return_value = {"error": {"code": 429, "message": "Quota exceeded"}}

        # 2nd call (retry) returns 200
        resp2 = MagicMock()
        resp2.status_code = 200
        resp2.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "Forecast model accuracy is 91.2%."}
                        ]
                    }
                }
            ]
        }

        mock_post.side_effect = [resp1, resp2]

        resp = auth_client.post(
            "/api/assistant/chat/",
            {"messages": [{"role": "user", "content": "How accurate is the forecast?"}]},
            format="json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "Forecast model accuracy is 91.2%." in data["reply"]
        assert "(offline mode)" not in data["reply"]
        assert mock_post.call_count == 2
        mock_sleep.assert_called_once_with(14.0)

    @patch("apps.assistant.providers.time.sleep")
    @patch("apps.assistant.providers.requests.post")
    def test_mocked_429_twice_leading_to_offline_fallback(self, mock_post, mock_sleep, auth_client, settings, sample_retail_setup):
        settings.LLM_PROVIDER = "gemini"
        settings.LLM_API_KEY = "test-gemini-key"
        settings.LLM_MODEL = "gemini-3.5-flash"

        # 1st call: 429 with retry delay in error body > 20s (tests capping at 20s)
        resp1 = MagicMock()
        resp1.status_code = 429
        resp1.headers = {}
        resp1.text = '{"error": {"code": 429, "message": "Resource exhausted, retry in 45s"}}'
        resp1.json.return_value = {
            "error": {
                "code": 429,
                "message": "Resource exhausted, retry in 45s",
                "details": [{"@type": "RetryInfo", "retryDelay": "45s"}],
            }
        }

        # 2nd call: still 429
        resp2 = MagicMock()
        resp2.status_code = 429
        resp2.headers = {}
        resp2.text = '{"error": {"code": 429, "message": "Resource exhausted"}}'
        resp2.json.return_value = {"error": {"code": 429, "message": "Resource exhausted"}}

        mock_post.side_effect = [resp1, resp2]

        resp = auth_client.post(
            "/api/assistant/chat/",
            {"messages": [{"role": "user", "content": "How accurate is the forecast?"}]},
            format="json",
        )
        assert resp.status_code == 200
        data = resp.json()
        # Falls back to offline mode
        assert "(offline mode)" in data["reply"]
        assert "LightGBM" in data["reply"]
        assert mock_post.call_count == 2
        # Verify delay was capped at 20.0s
        mock_sleep.assert_called_once_with(20.0)


class TestRetryDelayExtraction:
    def test_retry_after_header(self):
        from apps.assistant.providers import extract_retry_delay
        resp = MagicMock()
        resp.headers = {"Retry-After": "8"}
        assert extract_retry_delay(resp) == 8.0

    def test_retry_after_cap_at_20(self):
        from apps.assistant.providers import extract_retry_delay
        resp = MagicMock()
        resp.headers = {"Retry-After": "45"}
        assert extract_retry_delay(resp) == 20.0

    def test_details_retry_delay(self):
        from apps.assistant.providers import extract_retry_delay
        resp = MagicMock()
        resp.headers = {}
        resp.json.return_value = {
            "error": {"details": [{"@type": "RetryInfo", "retryDelay": "15.5s"}]}
        }
        assert extract_retry_delay(resp) == 15.5

    def test_default_delay_12(self):
        from apps.assistant.providers import extract_retry_delay
        resp = MagicMock()
        resp.headers = {}
        resp.json.return_value = {"error": {"message": "Rate limit exceeded"}}
        resp.text = "Rate limit exceeded"
        assert extract_retry_delay(resp) == 12.0



