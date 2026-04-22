"""LLM client abstraction with OpenAI-compatible Chat Completions support."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
import ssl
from dataclasses import dataclass
from typing import Protocol


DEFAULT_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
GROK_BASE_URL = "https://api.x.ai/v1"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_GROK_MODEL = "grok-4"


class LLMError(RuntimeError):
    """Raised when an LLM call cannot be completed."""


class LLMClient(Protocol):
    """Minimal text-generation interface used by the agent."""

    provider_name: str

    def generate(self, *, system: str, user: str, temperature: float = 0.3) -> str:
        """Return generated text for one prompt pair."""


@dataclass(slots=True)
class LLMSettings:
    """Runtime settings for an OpenAI-compatible chat endpoint."""

    provider: str = "auto"
    api_key: str | None = None
    base_url: str = DEFAULT_CHAT_COMPLETIONS_URL
    model: str = DEFAULT_MODEL
    timeout_seconds: int = 120
    max_retries: int = 4

    @classmethod
    def from_env(
        cls,
        provider: str = "auto",
        *,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ) -> "LLMSettings":
        is_grok = provider == "grok"
        resolved_api_key = (
            api_key
            or (os.getenv("XAI_API_KEY") if is_grok else None)
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("SOFTCOPYRIGHT_LLM_API_KEY")
        )
        resolved_base_url = (
            base_url
            or (os.getenv("XAI_BASE_URL") if is_grok else None)
            or os.getenv("OPENAI_BASE_URL")
            or os.getenv("SOFTCOPYRIGHT_LLM_BASE_URL")
            or (GROK_BASE_URL if is_grok else DEFAULT_CHAT_COMPLETIONS_URL)
        )
        resolved_model = (
            model
            or (os.getenv("XAI_MODEL") if is_grok else None)
            or os.getenv("SOFTCOPYRIGHT_LLM_MODEL")
            or os.getenv("OPENAI_MODEL")
            or (DEFAULT_GROK_MODEL if is_grok else DEFAULT_MODEL)
        )
        return cls(
            provider=provider,
            api_key=resolved_api_key,
            base_url=resolved_base_url,
            model=resolved_model,
        )


class OpenAICompatibleClient:
    """Call an OpenAI-compatible Chat Completions endpoint using stdlib urllib."""

    def __init__(self, settings: LLMSettings) -> None:
        if not settings.api_key:
            raise LLMError("LLM API key is missing. Set OPENAI_API_KEY or SOFTCOPYRIGHT_LLM_API_KEY.")
        self.settings = settings
        self.provider_name = "grok" if settings.provider == "grok" else "openai-compatible"
        self.endpoint = settings.base_url.rstrip("/")
        if not self.endpoint.endswith("/chat/completions"):
            self.endpoint = f"{self.endpoint}/chat/completions"

    def generate(self, *, system: str, user: str, temperature: float = 0.3) -> str:
        payload = {
            "model": self.settings.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
        }
        last_error: Exception | None = None
        for attempt in range(self.settings.max_retries + 1):
            request = urllib.request.Request(self.endpoint, data=data, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(request, timeout=self.settings.timeout_seconds) as response:
                    body = json.loads(response.read().decode("utf-8"))
                return body["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as exc:
                last_error = exc
                # 只有 429(限流) 和 5xx(后端宕机) 能缓解，400/401/403/404大概率是配置问题，直接抛出
                if exc.code not in {429, 500, 502, 503, 504}:
                    raise LLMError(f"LLM API 拒绝请求: HTTP {exc.code} - {exc.reason}")
                if attempt < self.settings.max_retries:
                    # 指数退避: 1s, 2s, 4s, 8s...
                    time.sleep(2 ** attempt)
            except (KeyError, IndexError, json.JSONDecodeError, urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
                if attempt < self.settings.max_retries:
                    time.sleep(2 ** attempt)
            except ssl.SSLError as exc:
                raise LLMError(
                    f"安全连接握手失败 (SSLError)。这通常是因为配置了不支持 HTTPS 的本地服务器（如 Ollama）却在 Base URL 中填了 'https://'。请检查您的 API 配置是否应该使用 'http://'。原始错误: {exc}"
                ) from exc
            except OSError as exc:
                last_error = exc
                if attempt < self.settings.max_retries:
                    time.sleep(2 ** attempt)
        raise LLMError(f"LLM 请求重试 {self.settings.max_retries} 次后仍失败: {last_error}")

    def generate_stream(self, *, system: str, user: str, temperature: float = 0.3):
        """Yield text chunks from a streaming Chat Completions response.

        Provides real-time token delivery for UI display. The caller
        iterates over this generator to receive incremental content.
        """
        payload = {
            "model": self.settings.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "stream": True,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
        }
        request = urllib.request.Request(self.endpoint, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.settings.timeout_seconds) as response:
                for raw_line in response:
                    decoded = raw_line.decode("utf-8").strip()
                    if not decoded or not decoded.startswith("data: "):
                        continue
                    if decoded == "data: [DONE]":
                        break
                    try:
                        chunk = json.loads(decoded[6:])
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        if content := delta.get("content", ""):
                            yield content
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue
        except (urllib.error.URLError, OSError) as exc:
            raise LLMError(f"LLM 流式请求失败: {exc}") from exc


class FallbackLLMClient:
    """Non-network fallback used for tests and offline demos."""

    provider_name = "fallback"

    def generate(self, *, system: str, user: str, temperature: float = 0.3) -> str:
        raise LLMError("fallback client intentionally does not synthesize model content")


def create_llm_client(settings: LLMSettings, *, required: bool = False) -> LLMClient | None:
    """Create a configured LLM client or return None when fallback is allowed."""

    if settings.provider == "fallback":
        return None
    try:
        return OpenAICompatibleClient(settings)
    except LLMError:
        if required:
            raise
        return None


def extract_json_object(text: str) -> object:
    """Extract a JSON object or array from a model response."""

    stripped = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", stripped, re.DOTALL | re.IGNORECASE)
    if fenced:
        stripped = fenced.group(1).strip()
    if stripped.startswith("{") or stripped.startswith("["):
        return json.loads(stripped)
    match = re.search(r"(\{.*\}|\[.*\])", stripped, re.DOTALL)
    if not match:
        raise ValueError("model response does not contain JSON")
    return json.loads(match.group(1))
