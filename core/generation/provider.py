from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
from typing import Mapping
from urllib import request

from core.runtime.client import ChatRequest, OpenAIChatRuntimeClient, RuntimeClientError
from core.runtime.config import OpenAICompatibleRuntimeConfig, STAGE_MAX_TOKENS_ENV
from core.runtime.errors import ProviderConfigurationError, ProviderError


ProviderConfig = OpenAICompatibleRuntimeConfig


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
        self.client = OpenAIChatRuntimeClient(
            config.to_runtime_profile(),
            opener=request.urlopen,
        )

    def generate(self, prompt_request: GenerationRequest) -> GenerationResponse:
        try:
            response = self.client.generate(
                ChatRequest(
                    stage=prompt_request.stage,
                    prompt=prompt_request.prompt,
                    response_format=prompt_request.response_format,
                    temperature=prompt_request.temperature,
                    system_prompt=prompt_request.system_prompt,
                    max_tokens=prompt_request.max_tokens,
                )
            )
        except RuntimeClientError as exc:
            message = str(exc).replace("runtime", "provider")
            raise ProviderError(message) from exc
        return GenerationResponse(content=response.content, model=response.model, raw=response.raw)


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
