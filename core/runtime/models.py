from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Mapping


@dataclass(frozen=True)
class RuntimeCapabilities:
    supports_response_format: bool = True
    response_format_mode: str = "best_effort"
    requires_manual_model_switch: bool = False
    single_model_per_runtime: bool = False
    supports_cross_provider_fallback: bool = True


@dataclass(frozen=True)
class RuntimeConstraint:
    code: str
    detail: str


@dataclass(frozen=True)
class RuntimeProfile:
    provider: str
    base_url: str
    api_key: str
    model: str
    timeout: float
    max_tokens: int
    stage_max_tokens: Mapping[str, int]
    name: str = "openai_compatible_generic"
    capabilities: RuntimeCapabilities = field(default_factory=RuntimeCapabilities)
    constraints: tuple[RuntimeConstraint, ...] = ()

    def max_tokens_for_stage(self, stage: str, explicit: int | None = None) -> int:
        if explicit is not None:
            return explicit
        return self.stage_max_tokens.get(stage, self.max_tokens)

    def with_model(self, model: str) -> "RuntimeProfile":
        next_manual_switch = self.capabilities.requires_manual_model_switch
        if self.model.startswith("apple-coreml:") and model.startswith("apple-coreml:") and self.model != model:
            next_manual_switch = True
        constraints = list(self.constraints)
        if model.startswith("apple-coreml:") and not any(
            item.code == "manual-apple-switch" for item in constraints
        ):
            constraints.append(
                RuntimeConstraint(
                    code="manual-apple-switch",
                    detail="Le runtime Apple local ne sert qu'un model_id a la fois; un checkpoint manuel peut etre requis.",
                )
            )
        return replace(
            self,
            model=model,
            capabilities=replace(self.capabilities, requires_manual_model_switch=next_manual_switch),
            constraints=tuple(constraints),
        )

    @property
    def provider_name(self) -> str | None:
        if ":" not in self.model:
            return None
        provider, _ = self.model.split(":", 1)
        provider = provider.strip()
        return provider or None


@dataclass(frozen=True)
class RuntimeHealth:
    ok: bool
    url: str
    status: str | None = None
    active_model: str | None = None
    available_models: list[str] | None = None
    detail: str | None = None
