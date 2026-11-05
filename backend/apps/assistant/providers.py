"""LLM provider abstraction with native tool calling for Anthropic and Gemini."""

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple
import requests

from apps.assistant.tools import TOOL_DECLARATIONS, TOOL_REGISTRY

logger = logging.getLogger(__name__)


def extract_retry_delay(resp: requests.Response) -> float:
    """Extract retry delay from Retry-After header or error body. Cap at 20s, default 12s."""
    delay: Optional[float] = None

    # 1. Retry-After header
    header_val = resp.headers.get("Retry-After")
    if header_val is not None:
        try:
            delay = float(header_val)
        except (ValueError, TypeError):
            pass

    # 2. JSON error body
    if delay is None:
        try:
            data = resp.json()
            if isinstance(data, dict):
                err = data.get("error", {})
                if isinstance(err, dict):
                    # Check Google RPC RetryInfo in details
                    for item in err.get("details", []):
                        if isinstance(item, dict) and "retryDelay" in item:
                            raw = str(item["retryDelay"]).rstrip("s")
                            delay = float(raw)
                            break
                    # Check error message
                    if delay is None and "message" in err:
                        m = re.search(r"retry (?:in|after) (\d+(?:\.\d+)?)s?", str(err["message"]), re.IGNORECASE)
                        if m:
                            delay = float(m.group(1))
        except Exception:
            pass

    # 3. Fallback regex on resp.text
    if delay is None and resp.text:
        m = re.search(r"retry (?:in|after) (\d+(?:\.\d+)?)s?", resp.text, re.IGNORECASE)
        if m:
            try:
                delay = float(m.group(1))
            except (ValueError, TypeError):
                pass

    if delay is None or delay < 0:
        delay = 12.0

    return min(delay, 20.0)


def post_with_retry(
    endpoint: str,
    start_time: float,
    max_total_seconds: float = 60.0,
    **kwargs: Any,
) -> requests.Response:
    """Send requests.post with single 429 retry keeping total duration under max_total_seconds."""
    per_call_timeout = kwargs.pop("timeout", 25.0)

    elapsed = time.monotonic() - start_time
    remaining = max(1.0, max_total_seconds - elapsed)
    kwargs["timeout"] = min(per_call_timeout, remaining)

    resp = requests.post(endpoint, **kwargs)

    if resp.status_code == 429:
        delay = extract_retry_delay(resp)
        elapsed = time.monotonic() - start_time
        remaining = max_total_seconds - elapsed
        if remaining > 1.0:
            wait_time = min(delay, max(0.0, remaining - 1.0))
            logger.warning("LLM returned 429 rate limit. Waiting %.1fs before retrying once.", wait_time)
            time.sleep(wait_time)

            elapsed = time.monotonic() - start_time
            remaining = max(1.0, max_total_seconds - elapsed)
            kwargs["timeout"] = min(per_call_timeout, remaining)
            resp = requests.post(endpoint, **kwargs)

    return resp


def truncate_json(data: Any, max_chars: int = 4000) -> str:
    """Serialize data to JSON and truncate if exceeding max_chars."""
    s = json.dumps(data, ensure_ascii=False)
    if len(s) > max_chars:
        return s[:max_chars] + "... (truncated)"
    return s


class AnthropicProvider:
    """Native tool calling integration with Anthropic Claude API."""

    def __init__(self, api_key: str, model: str = ""):
        self.api_key = api_key
        self.model = model.strip() if model else "claude-3-5-sonnet-20241022"
        self.endpoint = "https://api.anthropic.com/v1/messages"

    def chat(self, messages: List[Dict[str, str]], system_prompt: str) -> Tuple[str, List[str]]:
        tools_used: List[str] = []
        anthropic_tools = [
            {
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["parameters"],
            }
            for t in TOOL_DECLARATIONS
        ]

        # Format conversation messages for Anthropic
        conversation: List[Dict[str, Any]] = [
            {"role": m["role"], "content": m["content"]} for m in messages
        ]

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        start_time = time.monotonic()

        # Multi-turn tool execution loop capped at 5 iterations
        for _ in range(5):
            payload = {
                "model": self.model,
                "max_tokens": 1024,
                "system": system_prompt,
                "messages": conversation,
                "tools": anthropic_tools,
            }

            resp = post_with_retry(
                self.endpoint,
                start_time=start_time,
                max_total_seconds=60.0,
                headers=headers,
                json=payload,
                timeout=25,
            )
            if resp.status_code != 200:
                logger.error("Anthropic API error: %s - %s", resp.status_code, resp.text)
                raise RuntimeError(f"Anthropic API returned status {resp.status_code}")

            data = resp.json()
            stop_reason = data.get("stop_reason")
            content_blocks = data.get("content", [])

            conversation.append({"role": "assistant", "content": content_blocks})

            if stop_reason == "tool_use":
                tool_results_blocks = []
                for block in content_blocks:
                    if block.get("type") == "tool_use":
                        tool_name = block.get("name")
                        tool_input = block.get("input", {})
                        tool_use_id = block.get("id")

                        if tool_name not in tools_used:
                            tools_used.append(tool_name)

                        func = TOOL_REGISTRY.get(tool_name)
                        if func:
                            try:
                                res = func(**tool_input)
                            except Exception as err:
                                res = {"error": str(err)}
                        else:
                            res = {"error": f"Unknown tool: {tool_name}"}

                        tool_results_blocks.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": truncate_json(res),
                            }
                        )

                conversation.append({"role": "user", "content": tool_results_blocks})
            else:
                # Text answer completed
                text_parts = [b.get("text", "") for b in content_blocks if b.get("type") == "text"]
                return "".join(text_parts).strip(), tools_used

        # Fallback if loop finishes without final text
        return "Tool execution loop reached iteration limit.", tools_used


class GeminiProvider:
    """Native tool calling integration with Google Gemini API."""

    def __init__(self, api_key: str, model: str = ""):
        self.api_key = api_key.strip()
        cleaned_model = model.strip()
        if not cleaned_model:
            self.model = "gemini-3.5-flash"
        else:
            self.model = cleaned_model.replace(" ", "-")
        self.endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        )

    def chat(self, messages: List[Dict[str, str]], system_prompt: str) -> Tuple[str, List[str]]:
        tools_used: List[str] = []
        gemini_tools = [
            {
                "function_declarations": [
                    {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t["parameters"],
                    }
                    for t in TOOL_DECLARATIONS
                ]
            }
        ]

        # Convert conversation to Gemini contents
        contents: List[Dict[str, Any]] = []
        for m in messages:
            role = "user" if m["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})

        start_time = time.monotonic()

        # Multi-turn tool execution loop capped at 5 iterations
        for _ in range(5):
            payload = {
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": contents,
                "tools": gemini_tools,
            }

            resp = post_with_retry(
                self.endpoint,
                start_time=start_time,
                max_total_seconds=60.0,
                params={"key": self.api_key},
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60,
            )

            if resp.status_code != 200:
                logger.error("Gemini API error: %s - %s", resp.status_code, resp.text)
                raise RuntimeError(f"Gemini API returned status {resp.status_code}")

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise RuntimeError("No candidate responses returned from Gemini.")

            content_obj = candidates[0].get("content", {})
            parts = content_obj.get("parts", [])

            # Add model turn to conversation history
            contents.append({"role": "model", "parts": parts})

            function_calls = [p.get("functionCall") for p in parts if "functionCall" in p]

            if function_calls:
                response_parts = []
                for fc in function_calls:
                    tool_name = fc.get("name")
                    tool_args = fc.get("args", {})

                    if tool_name not in tools_used:
                        tools_used.append(tool_name)

                    func = TOOL_REGISTRY.get(tool_name)
                    if func:
                        try:
                            res = func(**tool_args)
                        except Exception as err:
                            res = {"error": str(err)}
                    else:
                        res = {"error": f"Unknown tool: {tool_name}"}

                    fn_resp: Dict[str, Any] = {
                        "name": tool_name,
                        "response": {"result": res},
                    }
                    if fc.get("id"):
                        fn_resp["id"] = fc.get("id")

                    response_parts.append({"functionResponse": fn_resp})

                # Return function response turn
                contents.append({"role": "user", "parts": response_parts})
            else:
                # Text answer received
                text_parts = [p.get("text", "") for p in parts if "text" in p]
                return "".join(text_parts).strip(), tools_used

        return "Tool execution loop reached iteration limit.", tools_used
