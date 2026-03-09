from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
import json
import os
import socket
from typing import Mapping
from urllib import error, request


class ProviderError(RuntimeError):
    """Raised when a text generation provider fails."""


class ProviderConfigurationError(ProviderError):
    """Raised when the provider environment is incomplete."""


STAGE_MAX_TOKENS_ENV = {
    "structure": "ANE_MAX_TOKENS_STRUCTURE",
    "draft": "ANE_MAX_TOKENS_DRAFT",
    "critique": "ANE_MAX_TOKENS_CRITIQUE",
    "rewrite": "ANE_MAX_TOKENS_REWRITE",
    "gate": "ANE_MAX_TOKENS_GATE",
    "repair": "ANE_MAX_TOKENS_REPAIR",
    "memory": "ANE_MAX_TOKENS_MEMORY",
}


def _parse_positive_int(raw_value: str, *, env_name: str) -> int:
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ProviderConfigurationError(f"{env_name} doit être un entier.") from exc
    if value <= 0:
        raise ProviderConfigurationError(f"{env_name} doit être supérieur à zéro.")
    return value


@dataclass(frozen=True)
class ProviderConfig:
    provider: str
    base_url: str
    api_key: str
    model: str
    timeout: float
    max_tokens: int
    stage_max_tokens: Mapping[str, int]

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "ProviderConfig":
        source = env or os.environ
        provider = source.get("ANE_PROVIDER", "openai_compatible").strip() or "openai_compatible"
        base_url = source.get("ANE_BASE_URL", "").strip()
        model = source.get("ANE_MODEL", "").strip()
        api_key = source.get("ANE_API_KEY", "").strip()
        timeout_value = source.get("ANE_TIMEOUT", "60").strip() or "60"
        max_tokens_value = source.get("ANE_MAX_TOKENS", "4096").strip() or "4096"

        try:
            timeout = float(timeout_value)
        except ValueError as exc:
            raise ProviderConfigurationError("ANE_TIMEOUT doit être un nombre.") from exc

        max_tokens = _parse_positive_int(max_tokens_value, env_name="ANE_MAX_TOKENS")
        stage_max_tokens: dict[str, int] = {}
        for stage_name, env_name in STAGE_MAX_TOKENS_ENV.items():
            raw_stage_value = source.get(env_name, "").strip()
            if not raw_stage_value:
                continue
            stage_max_tokens[stage_name] = _parse_positive_int(raw_stage_value, env_name=env_name)

        return cls(
            provider=provider,
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout=timeout,
            max_tokens=max_tokens,
            stage_max_tokens=stage_max_tokens,
        )

    def max_tokens_for_stage(self, stage: str, explicit: int | None = None) -> int:
        if explicit is not None:
            return explicit
        return self.stage_max_tokens.get(stage, self.max_tokens)

    def with_model(self, model: str) -> "ProviderConfig":
        return replace(self, model=model)


@dataclass(frozen=True)
class GenerationRequest:
    stage: str
    prompt: str
    response_format: str = "text"
    temperature: float = 0.2
    system_prompt: str | None = None
    max_tokens: int | None = None


@dataclass(frozen=True)
class GenerationResponse:
    content: str
    model: str | None = None
    raw: dict[str, object] | None = None


class GenerationProvider(ABC):
    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResponse:
        raise NotImplementedError


class OpenAICompatibleProvider(GenerationProvider):
    def __init__(self, config: ProviderConfig):
        if not config.base_url:
            raise ProviderConfigurationError("ANE_BASE_URL est requis pour le provider openai_compatible.")
        if not config.model:
            raise ProviderConfigurationError("ANE_MODEL est requis pour le provider openai_compatible.")
        self.config = config

    def generate(self, prompt_request: GenerationRequest) -> GenerationResponse:
        payload: dict[str, object] = {
            "model": self.config.model,
            "messages": self._build_messages(prompt_request),
            "temperature": prompt_request.temperature,
            "max_tokens": self.config.max_tokens_for_stage(
                prompt_request.stage,
                prompt_request.max_tokens,
            ),
        }
        if prompt_request.response_format == "json":
            payload["response_format"] = {"type": "json_object"}

        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        http_request = request.Request(
            self._chat_completions_url(),
            data=body,
            headers=headers,
            method="POST",
        )

        try:
            with request.urlopen(http_request, timeout=self.config.timeout) as response:
                raw_payload = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise ProviderError(
                f"Le provider a répondu avec HTTP {exc.code} pendant l'étape '{prompt_request.stage}': {details}"
            ) from exc
        except error.URLError as exc:
            raise ProviderError(
                f"Impossible de joindre le provider pendant l'étape '{prompt_request.stage}': {exc.reason}"
            ) from exc
        except (TimeoutError, socket.timeout) as exc:
            raise ProviderError(
                f"Timeout du provider pendant l'étape '{prompt_request.stage}' après {self.config.timeout:.0f}s."
            ) from exc
        except json.JSONDecodeError as exc:
            raise ProviderError(
                f"Réponse non JSON du provider pendant l'étape '{prompt_request.stage}'."
            ) from exc

        try:
            choice = raw_payload["choices"][0]
            message = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(
                f"Réponse OpenAI-compatible invalide pendant l'étape '{prompt_request.stage}'."
            ) from exc

        content = self._normalize_message_content(message)
        return GenerationResponse(
            content=content,
            model=str(raw_payload.get("model", self.config.model)),
            raw=raw_payload,
        )

    def _build_messages(self, prompt_request: GenerationRequest) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if prompt_request.system_prompt:
            messages.append({"role": "system", "content": prompt_request.system_prompt})
        messages.append({"role": "user", "content": prompt_request.prompt})
        return messages

    def _chat_completions_url(self) -> str:
        base = self.config.base_url.rstrip("/")
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
        raise ProviderError("Le provider n'a pas renvoyé de contenu texte exploitable.")


class MockGenerationProvider(GenerationProvider):
    def __init__(self, responses: Mapping[str, object]):
        self._responses = {
            stage: list(value) if isinstance(value, list) else [value]
            for stage, value in responses.items()
        }
        self.requests: list[GenerationRequest] = []

    def generate(self, prompt_request: GenerationRequest) -> GenerationResponse:
        self.requests.append(prompt_request)
        queue = self._responses.get(prompt_request.stage)
        if not queue:
            raise ProviderError(f"Aucune réponse mock configurée pour l'étape '{prompt_request.stage}'.")

        next_value = queue.pop(0)
        if isinstance(next_value, Exception):
            raise next_value
        if isinstance(next_value, (dict, list)):
            content = json.dumps(next_value, ensure_ascii=False)
        else:
            content = str(next_value)

        return GenerationResponse(content=content, model="mock")


def build_provider_from_env(env: Mapping[str, str] | None = None) -> GenerationProvider:
    config = ProviderConfig.from_env(env)
    if config.provider != "openai_compatible":
        raise ProviderConfigurationError(
            f"Provider non supporté: {config.provider}. Utilisez ANE_PROVIDER=openai_compatible."
        )
    return OpenAICompatibleProvider(config)


def clone_provider_with_model(provider: GenerationProvider, model: str) -> GenerationProvider:
    if not model:
        return provider
    if isinstance(provider, OpenAICompatibleProvider):
        if provider.config.model == model:
            return provider
        return OpenAICompatibleProvider(provider.config.with_model(model))
    return provider
