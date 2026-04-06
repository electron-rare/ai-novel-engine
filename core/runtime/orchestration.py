from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable

from core.runtime.config import openai_base_url_for_model, runtime_probe_profile
from core.runtime.health import current_apple_model, probe_runtime_health, runtime_model_ids, wait_for_expected_apple_model
from core.runtime.profiles import runtime_probe_name


JsonFetcher = Callable[[str, float], Any]


@dataclass(frozen=True)
class RuntimeExecutionPlan:
    model: str
    openai_base_url: str
    timeout_seconds: int
    requires_native_ollama_preflight: bool
    native_preflight_timeout_seconds: float
    probe_profile_name: str


@dataclass(frozen=True)
class RuntimeCheckpointSignals:
    core_health_ok: bool
    apple_model_active: str | None
    ollama_openai_runtime_ready: bool


def runtime_timeout_for_model(model: str, *, smoke_timeout_seconds: int) -> int:
    if model.startswith("apple-coreml:"):
        return max(600, smoke_timeout_seconds)
    return max(120, smoke_timeout_seconds)


def build_runtime_execution_plan(
    model: str,
    *,
    core_base_url: str,
    ollama_runtime: str,
    ollama_openai_base_url: str,
    smoke_timeout_seconds: int,
) -> RuntimeExecutionPlan:
    openai_base_url = openai_base_url_for_model(
        model,
        core_base_url=core_base_url,
        ollama_runtime=ollama_runtime,
        ollama_openai_base_url=ollama_openai_base_url,
    )
    timeout_seconds = runtime_timeout_for_model(model, smoke_timeout_seconds=smoke_timeout_seconds)
    requires_native_preflight = model.startswith("ollama:") and ollama_runtime == "native"
    probe_kind = "ollama_openai" if openai_base_url == ollama_openai_base_url and model.startswith("ollama:") else "core"
    return RuntimeExecutionPlan(
        model=model,
        openai_base_url=openai_base_url,
        timeout_seconds=timeout_seconds,
        requires_native_ollama_preflight=requires_native_preflight,
        native_preflight_timeout_seconds=min(45.0, float(timeout_seconds)),
        probe_profile_name=runtime_probe_name(probe_kind),
    )


def collect_checkpoint_runtime_signals(
    model: str,
    *,
    core_base_url: str,
    apple_runtime_url: str,
    apple_model_ready_timeout_seconds: float,
    apple_model_poll_interval_seconds: float,
    ollama_runtime: str,
    ollama_openai_base_url: str,
    json_fetcher: JsonFetcher,
) -> RuntimeCheckpointSignals:
    core_profile = runtime_probe_profile(core_base_url, name=runtime_probe_name("core"))
    core_health = probe_runtime_health(
        core_profile,
        health_fetcher=json_fetcher,
        json_fetcher=json_fetcher,
    )

    apple_model = None
    if model.startswith("apple-coreml:"):
        apple_model = wait_for_expected_apple_model(
            apple_runtime_url,
            model.split(":", 1)[1],
            json_fetcher=json_fetcher,
            timeout_seconds=apple_model_ready_timeout_seconds,
            poll_interval_seconds=apple_model_poll_interval_seconds,
        )

    ollama_ready = False
    if model.startswith("ollama:") and ollama_runtime == "openai_compatible":
        ollama_ready = model in openai_runtime_model_ids(
            ollama_openai_base_url,
            json_fetcher=json_fetcher,
            profile_name=runtime_probe_name("ollama_openai"),
        )

    return RuntimeCheckpointSignals(
        core_health_ok=core_health.ok,
        apple_model_active=apple_model,
        ollama_openai_runtime_ready=ollama_ready,
    )


def openai_runtime_model_ids(base_url: str, *, json_fetcher: JsonFetcher, profile_name: str) -> set[str]:
    profile = runtime_probe_profile(base_url, name=profile_name)
    health = probe_runtime_health(
        profile,
        health_fetcher=json_fetcher,
        json_fetcher=json_fetcher,
    )
    if not health.ok or not health.available_models:
        return set()
    try:
        model_ids = runtime_model_ids(profile, json_fetcher=json_fetcher)
    except (OSError, json.JSONDecodeError, ValueError):
        return set(health.available_models)
    return model_ids or set(health.available_models)


def missing_ollama_models(
    required_models: list[str],
    *,
    tags_url: str,
    json_fetcher: JsonFetcher,
) -> list[str]:
    try:
        payload = json_fetcher(tags_url, 10.0)
    except (OSError, json.JSONDecodeError, ValueError):
        return []
    models = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(models, list):
        return []
    names = {
        str(item.get("name", "")).strip()
        for item in models
        if isinstance(item, dict) and str(item.get("name", "")).strip()
    }
    return [model for model in required_models if model not in names]


def read_current_apple_model(apple_runtime_url: str, *, json_fetcher: JsonFetcher) -> str | None:
    return current_apple_model(
        apple_runtime_url,
        json_fetcher=json_fetcher,
    )
