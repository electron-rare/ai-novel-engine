from __future__ import annotations

from dataclasses import dataclass
import json
import random
import socket
import time
from typing import Callable
from urllib import error, request

from core.runtime.models import RuntimeProfile


class RuntimeClientError(RuntimeError):
    """Raised when the runtime cannot complete a generation request."""


@dataclass(frozen=True)
class ChatRequest:
    stage: str
    prompt: str
    response_format: str = "text"
    temperature: float = 0.2
    system_prompt: str | None = None
    max_tokens: int | None = None


@dataclass(frozen=True)
class ChatResponse:
    content: str
    model: str | None = None
    raw: dict[str, object] | None = None


class OpenAIChatRuntimeClient:
    def __init__(
        self,
        profile: RuntimeProfile,
        *,
        opener: Callable[..., object] | None = None,
        sleeper: Callable[[float], None] | None = None,
        jitter: Callable[[float, float], float] | None = None,
    ) -> None:
        self.profile = profile
        self._opener = opener or request.urlopen
        self._sleeper = sleeper or time.sleep
        self._jitter = jitter or random.uniform

    def generate(self, chat_request: ChatRequest) -> ChatResponse:
        payload: dict[str, object] = {
            "model": self.profile.model,
            "messages": self._build_messages(chat_request),
            "temperature": chat_request.temperature,
            "max_tokens": self.profile.max_tokens_for_stage(
                chat_request.stage,
                chat_request.max_tokens,
            ),
        }
        if chat_request.response_format == "json" and self.profile.capabilities.supports_response_format:
            payload["response_format"] = {"type": "json_object"}

        http_request = request.Request(
            self._chat_completions_url(),
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        raw_payload = self._request_json(http_request, stage=chat_request.stage)

        try:
            choice = raw_payload["choices"][0]
            message = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeClientError(
                f"Réponse OpenAI-compatible invalide pendant l'étape '{chat_request.stage}'."
            ) from exc

        return ChatResponse(
            content=self._normalize_message_content(message),
            model=str(raw_payload.get("model", self.profile.model)),
            raw=raw_payload,
        )

    def _request_json(self, http_request: request.Request, *, stage: str) -> dict[str, object]:
        retryable_http_codes = {429, 500, 502, 503}
        max_retries = 3
        base_delay = 1.0
        max_delay = 10.0
        last_exc: Exception | None = None

        for attempt in range(max_retries):
            try:
                with self._opener(http_request, timeout=self.profile.timeout) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                if not isinstance(payload, dict):
                    raise RuntimeClientError(
                        f"Réponse JSON inattendue pendant l'étape '{stage}'."
                    )
                return payload
            except error.HTTPError as exc:
                if exc.code in retryable_http_codes and attempt < max_retries - 1:
                    last_exc = exc
                    self._sleep_backoff(base_delay, max_delay, attempt)
                    continue
                details = exc.read().decode("utf-8", errors="replace")
                raise RuntimeClientError(
                    f"Le runtime a répondu avec HTTP {exc.code} pendant l'étape '{stage}': {details}"
                ) from exc
            except (error.URLError, TimeoutError, socket.timeout) as exc:
                if attempt < max_retries - 1:
                    last_exc = exc
                    self._sleep_backoff(base_delay, max_delay, attempt)
                    continue
                if isinstance(exc, error.URLError):
                    raise RuntimeClientError(
                        f"Impossible de joindre le runtime pendant l'étape '{stage}': {exc.reason}"
                    ) from exc
                raise RuntimeClientError(
                    f"Timeout du runtime pendant l'étape '{stage}' après {self.profile.timeout:.0f}s."
                ) from exc
            except json.JSONDecodeError as exc:
                raise RuntimeClientError(
                    f"Réponse non JSON du runtime pendant l'étape '{stage}'."
                ) from exc

        raise RuntimeClientError(
            f"Le runtime a échoué après {max_retries} tentatives pendant l'étape '{stage}'."
        ) from last_exc

    def _sleep_backoff(self, base_delay: float, max_delay: float, attempt: int) -> None:
        delay = min(base_delay * (2 ** attempt), max_delay)
        delay += self._jitter(0, delay * 0.25)
        self._sleeper(delay)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.profile.api_key:
            headers["Authorization"] = f"Bearer {self.profile.api_key}"
        return headers

    def _build_messages(self, chat_request: ChatRequest) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if chat_request.system_prompt:
            messages.append({"role": "system", "content": chat_request.system_prompt})
        messages.append({"role": "user", "content": chat_request.prompt})
        return messages

    def _chat_completions_url(self) -> str:
        base = self.profile.base_url.rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        if base.endswith("/v1"):
            return f"{base}/chat/completions"
        return f"{base}/v1/chat/completions"

    def _normalize_message_content(self, message: object) -> str:
        if isinstance(message, str):
            return message
        if isinstance(message, list):
            parts: list[str] = []
            for item in message:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
            if parts:
                return "\n".join(parts)
        raise RuntimeClientError("Le runtime n'a pas renvoyé de contenu texte exploitable.")
