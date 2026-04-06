from __future__ import annotations

from dataclasses import dataclass, replace
import os
from typing import Mapping

from core.runtime.errors import ProviderConfigurationError
from core.runtime.models import RuntimeCapabilities, RuntimeConstraint, RuntimeProfile
from core.runtime.profiles import PROFILE_OPENAI_PROBE, runtime_profile_name_for_model


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


def _runtime_capabilities(model: str) -> RuntimeCapabilities:
    is_apple_runtime = model.startswith("apple-coreml:")
    return RuntimeCapabilities(
        supports_response_format=True,
        response_format_mode="best_effort",
        requires_manual_model_switch=is_apple_runtime,
        single_model_per_runtime=is_apple_runtime,
        supports_cross_provider_fallback=not is_apple_runtime,
    )


def _runtime_constraints(model: str) -> tuple[RuntimeConstraint, ...]:
    constraints: list[RuntimeConstraint] = [
        RuntimeConstraint(
            code="json-best-effort",
            detail="Le contrat JSON reste best-effort; ANE doit garder ses retries applicatifs.",
        )
    ]
    if not model.startswith("apple-coreml:"):
        return tuple(constraints)
    constraints.append(
        RuntimeConstraint(
            code="manual-apple-switch",
            detail="Le runtime Apple local ne sert qu'un model_id a la fois; un checkpoint manuel peut etre requis.",
        )
    )
    constraints.append(
        RuntimeConstraint(
            code="apple_single_model_runtime",
            detail="Le runtime Apple ne sert qu'un seul model_id a la fois.",
        )
    )
    return tuple(constraints)


@dataclass(frozen=True)
class OpenAICompatibleRuntimeConfig:
    provider: str
    base_url: str
    api_key: str
    model: str
    timeout: float
    max_tokens: int
    stage_max_tokens: Mapping[str, int]

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "OpenAICompatibleRuntimeConfig":
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

    def with_model(self, model: str) -> "OpenAICompatibleRuntimeConfig":
        return replace(self, model=model)

    def to_runtime_profile(self) -> RuntimeProfile:
        return RuntimeProfile(
            name=runtime_profile_name_for_model(self.model),
            provider=self.provider,
            base_url=self.base_url,
            api_key=self.api_key,
            model=self.model,
            timeout=self.timeout,
            max_tokens=self.max_tokens,
            stage_max_tokens=self.stage_max_tokens,
            capabilities=_runtime_capabilities(self.model),
            constraints=_runtime_constraints(self.model),
        )


def runtime_probe_profile(
    base_url: str,
    *,
    timeout: float = 10.0,
    model: str = "runtime-probe",
    provider: str = "openai_compatible",
    name: str = PROFILE_OPENAI_PROBE,
) -> RuntimeProfile:
    profile = OpenAICompatibleRuntimeConfig(
        provider=provider,
        base_url=base_url,
        api_key="",
        model=model,
        timeout=timeout,
        max_tokens=1,
        stage_max_tokens={},
    ).to_runtime_profile()
    return replace(profile, name=name)


def openai_base_url_for_model(
    model: str,
    *,
    core_base_url: str,
    ollama_runtime: str,
    ollama_openai_base_url: str,
) -> str:
    if model.startswith("ollama:") and ollama_runtime == "openai_compatible":
        return ollama_openai_base_url
    return core_base_url
