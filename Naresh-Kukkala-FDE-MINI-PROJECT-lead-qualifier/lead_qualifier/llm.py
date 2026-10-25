"""Thin, dependency-light LLM client with throttling, retries and a circuit breaker.

Providers are called over plain HTTPS with `requests` so there is no SDK lock-in:
    anthropic | openai | groq (OpenAI-compatible) | gemini | mock (offline)
"""
from __future__ import annotations

import json
import logging
import os
import random
import re
import time
from typing import Optional

import requests

log = logging.getLogger(__name__)

KEY_ENV = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY",
           "groq": "GROQ_API_KEY", "gemini": "GEMINI_API_KEY"}


class LLMError(Exception):
    """Base error. `retryable` tells the retry loop whether trying again can help."""
    def __init__(self, msg, retryable=True, retry_after: Optional[float] = None):
        super().__init__(msg)
        self.retryable = retryable
        self.retry_after = retry_after


class CircuitOpen(LLMError):
    def __init__(self):
        super().__init__("circuit breaker open: too many consecutive failures", retryable=False)


def extract_json(text: str):
    """Parse JSON from a model reply, tolerating ```json fences and leading prose."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = min([i for i in (text.find("{"), text.find("[")) if i != -1], default=-1)
        if start == -1:
            raise
        end = max(text.rfind("}"), text.rfind("]"))
        return json.loads(text[start:end + 1])


class LLMClient:
    def __init__(self, cfg: dict, provider: Optional[str] = None, model: Optional[str] = None,
                 company_cfg: Optional[dict] = None):
        self.cfg = cfg
        self.provider = (provider or cfg["provider"]).lower()
        self.model = model or cfg["models"].get(self.provider)
        self.timeout = cfg.get("timeout_seconds", 60)
        self.max_retries = cfg.get("max_retries", 4)
        self.backoff = cfg.get("backoff_base_seconds", 2)
        self.min_interval = 60.0 / max(1, cfg.get("requests_per_minute", 20))
        self.breaker_limit = cfg.get("circuit_breaker_failures", 3)
        self.temperature = cfg.get("temperature", 0.3)
        self.max_tokens = cfg.get("max_output_tokens", 8000)
        self._last_call = 0.0
        self.consecutive_failures = 0
        self.stats = {"api_calls": 0, "retries": 0, "failures": 0, "rate_limited": 0}
        self.api_key = None
        if self.provider != "mock":
            env = KEY_ENV.get(self.provider)
            if env is None:
                raise ValueError(f"Unknown provider '{self.provider}'. Use one of {list(KEY_ENV) + ['mock']}")
            self.api_key = os.getenv(env)
            if not self.api_key:
                raise ValueError(f"{env} is not set. Export it, or run with --provider mock for an offline dry run.")
        if self.provider == "mock":
            from .mock_llm import MockLLM
            self._mock = MockLLM(company_cfg or {})

    # ---------------- public ----------------
    @property
    def breaker_open(self) -> bool:
        return self.consecutive_failures >= self.breaker_limit

    def complete_json(self, system: str, user: str):
        """Call the model and return parsed JSON. Retries transient errors and malformed JSON."""
        if self.breaker_open:
            raise CircuitOpen()
        last_err: Optional[LLMError] = None
        for attempt in range(self.max_retries + 1):
            if attempt:
                self.stats["retries"] += 1
                wait = last_err.retry_after if (last_err and last_err.retry_after) else self.backoff * (2 ** (attempt - 1))
                wait += random.uniform(0, 0.5 * self.backoff)  # jitter avoids thundering herd
                log.warning("Retry %d/%d in %.1fs after: %s", attempt, self.max_retries, wait, last_err)
                time.sleep(wait)
            try:
                text = self._call(system, user)
                data = extract_json(text)
                self.consecutive_failures = 0
                return data
            except LLMError as e:
                last_err = e
                if not e.retryable:
                    break
            except (json.JSONDecodeError, ValueError) as e:
                last_err = LLMError(f"malformed JSON from model: {e}")
        self.stats["failures"] += 1
        self.consecutive_failures += 1
        raise last_err or LLMError("unknown failure")

    # ---------------- transport ----------------
    def _throttle(self):
        if self.provider == "mock":
            return
        gap = time.monotonic() - self._last_call
        if gap < self.min_interval:
            time.sleep(self.min_interval - gap)
        self._last_call = time.monotonic()

    def _call(self, system: str, user: str) -> str:
        self._throttle()
        self.stats["api_calls"] += 1
        if self.provider == "mock":
            return self._mock.complete(system, user)
        try:
            if self.provider == "anthropic":
                return self._anthropic(system, user)
            if self.provider in ("openai", "groq"):
                return self._openai_compatible(system, user)
            if self.provider == "gemini":
                return self._gemini(system, user)
        except requests.Timeout:
            raise LLMError(f"timeout after {self.timeout}s")
        except requests.ConnectionError as e:
            raise LLMError(f"connection error: {e}")
        raise LLMError(f"unsupported provider {self.provider}", retryable=False)

    def _post(self, url, headers, payload) -> dict:
        r = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        if r.status_code == 429:
            self.stats["rate_limited"] += 1
            ra = r.headers.get("retry-after")
            raise LLMError("rate limited (429)", retry_after=float(ra) if ra and ra.replace(".", "").isdigit() else None)
        if r.status_code >= 500 or r.status_code == 408 or r.status_code == 529:
            raise LLMError(f"server error {r.status_code}: {r.text[:200]}")
        if r.status_code >= 400:  # auth / bad request: retrying will not help
            raise LLMError(f"client error {r.status_code}: {r.text[:300]}", retryable=False)
        return r.json()

    def _anthropic(self, system, user):
        data = self._post(
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            {"model": self.model, "max_tokens": self.max_tokens, "temperature": self.temperature,
             "system": system, "messages": [{"role": "user", "content": user}]},
        )
        if data.get("stop_reason") == "max_tokens":
            raise LLMError("response truncated (max_tokens)")
        return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")

    def _openai_compatible(self, system, user):
        base = "https://api.groq.com/openai/v1" if self.provider == "groq" else "https://api.openai.com/v1"
        data = self._post(
            f"{base}/chat/completions",
            {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            {"model": self.model, "temperature": self.temperature, "max_tokens": self.max_tokens,
             "response_format": {"type": "json_object"},
             "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
        )
        choice = data["choices"][0]
        if choice.get("finish_reason") == "length":
            raise LLMError("response truncated (length)")
        return choice["message"]["content"]

    def _gemini(self, system, user):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        data = self._post(
            url, {"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
            {"systemInstruction": {"parts": [{"text": system}]},
             "contents": [{"role": "user", "parts": [{"text": user}]}],
             "generationConfig": {"temperature": self.temperature, "maxOutputTokens": self.max_tokens,
                                  "responseMimeType": "application/json"}},
        )
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            raise LLMError(f"unexpected Gemini response: {str(data)[:200]}")
