from __future__ import annotations

import json
import http.client
import socket
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from backend.app.core.config import settings


class LLMClient:
    """OpenAI-compatible chat client used for content and compliance tasks.

    DeepSeek, OpenAI, Claude-compatible gateways, and many internal model
    proxies can expose this shape. When no API key is configured the client is
    disabled and callers fall back to deterministic local logic.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: int = 30,
        max_retries: int = 0,
        retry_base_seconds: float = 1.5,
        reasoning_effort: str = "",
        thinking_enabled: bool = False,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, max_retries)
        self.retry_base_seconds = max(0.0, retry_base_seconds)
        self.reasoning_effort = reasoning_effort
        self.thinking_enabled = thinking_enabled
        self.enabled = bool(api_key)
        self.last_error = ""

    @classmethod
    def from_settings(cls) -> "LLMClient":
        return cls(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
            retry_base_seconds=settings.llm_retry_base_seconds,
            reasoning_effort=settings.llm_reasoning_effort,
            thinking_enabled=settings.llm_thinking_enabled,
        )

    def generate_tweet(self, payload: Dict[str, Any]) -> Optional[str]:
        system = (
            "You are a financial social media editor. Generate original X posts "
            "that are concise, factual, compliant, and never investment advice."
        )
        user = f"""
Create one X post from this JSON payload.
Return only the post text, no markdown.

Rules:
- 280 characters or fewer.
- Include 3 to 5 provided hashtags.
- Include "Not investment advice." for English or "不构成投资建议。" for Chinese.
- Do not promise returns, give buy/sell instructions, or make price predictions.
- If verification_status is unverified or partially_verified, attribute cautiously.
- Use the requested style:
  * professional_news: concise market bulletin, neutral and source-aware.
  * commentary: analytical market observation, still factual and non-advisory.
  * educational: plain-language explainer, helpful but not promotional.
- Do not copy any source wording verbatim; synthesize the event in original wording.

Payload:
{json.dumps(payload, ensure_ascii=False, indent=2)}
"""
        return self._chat_text(system, user)

    def review_compliance(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        system = "You are a strict financial compliance reviewer for public X posts."
        user = f"""
Review the content for financial compliance.
Return strict JSON with keys: pass(boolean), risk_level(low|medium|high|blocked), issues(array), revision_instruction(string).

Rules:
- Block investment advice, return promises, price predictions, hype, or confirmed wording for unverified claims.
- Medium or above requires human review.

Payload:
{json.dumps(payload, ensure_ascii=False, indent=2)}
"""
        text = self._chat_text(system, user, response_format={"type": "json_object"}, use_reasoning=False)
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    def extract_financial_entities(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        system = "You extract structured financial entities and event types from short X posts."
        user = f"""
Return strict JSON for this financial post.

Schema:
{{
  "entities": ["canonical entity names"],
  "event_type": "crypto_etf|central_bank|earnings|regulation|macro_data|commodity|market_move",
  "entity_types": {{"entity": "company|ticker|crypto_asset|etf|person|institution|country_region|macro_indicator|product|event|commodity|other"}}
}}

Rules:
- Use canonical names when obvious, e.g. BTC -> Bitcoin, NVDA -> Nvidia.
- Include companies, tickers, crypto assets, ETFs/funds, people, institutions, countries/regions, macro indicators, products, events, and commodities.
- Return JSON only.

Payload:
{json.dumps(payload, ensure_ascii=False, indent=2)}
"""
        text = self._chat_text(system, user, response_format={"type": "json_object"}, use_reasoning=False)
        if not text:
            return None
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None
        entities = data.get("entities", [])
        event_type = data.get("event_type")
        if not isinstance(entities, list) or not isinstance(event_type, str):
            return None
        return {
            "entities": [str(entity).strip() for entity in entities if str(entity).strip()],
            "event_type": event_type,
            "entity_types": data.get("entity_types", {}) if isinstance(data.get("entity_types", {}), dict) else {},
        }

    def _chat_text(
        self,
        system: str,
        user: str,
        response_format: Optional[Dict[str, str]] = None,
        use_reasoning: bool = True,
    ) -> Optional[str]:
        if not self.enabled:
            self.last_error = "disabled"
            return None
        self.last_error = ""
        body: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.4,
        }
        if use_reasoning and self.reasoning_effort:
            body["reasoning_effort"] = self.reasoning_effort
        if use_reasoning and self.thinking_enabled:
            body["thinking"] = {"type": "enabled"}
        if response_format:
            body["response_format"] = response_format
        encoded_body = json.dumps(body).encode("utf-8")
        endpoint = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        for attempt in range(self.max_retries + 1):
            request = urllib.request.Request(endpoint, data=encoded_body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    data = json.loads(response.read().decode("utf-8"))
                return data.get("choices", [{}])[0].get("message", {}).get("content")
            except urllib.error.HTTPError as exc:
                if not self._should_retry_http(exc.code) or attempt >= self.max_retries:
                    self.last_error = f"http_{exc.code}"
                    return None
            except (
                urllib.error.URLError,
                http.client.HTTPException,
                TimeoutError,
                socket.timeout,
                ConnectionResetError,
                OSError,
                json.JSONDecodeError,
            ) as exc:
                if attempt >= self.max_retries:
                    self.last_error = type(exc).__name__
                    return None
            self._sleep_before_retry(attempt)
        return None

    @staticmethod
    def _should_retry_http(status_code: int) -> bool:
        return status_code in {408, 409, 425, 429} or status_code >= 500

    def _sleep_before_retry(self, attempt: int) -> None:
        if self.retry_base_seconds <= 0:
            return
        time.sleep(min(self.retry_base_seconds * (2**attempt), 8.0))
