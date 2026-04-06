from __future__ import annotations

from core.runtime.errors import ProviderError


def model_provider_name(model: str | None) -> str | None:
    if not model or ":" not in model:
        return None
    provider, _ = model.split(":", 1)
    provider = provider.strip()
    return provider or None


def is_cross_apple_runtime_switch(base_model: str | None, candidate: str | None) -> bool:
    if not base_model or not candidate or base_model == candidate:
        return False
    return base_model.startswith("apple-coreml:") and candidate.startswith("apple-coreml:")


def default_repair_fallback_model(model: str | None) -> str | None:
    mapping = {
        "ollama:qwen2.5:1.5b": "ollama:qwen2.5:7b",
        "apple-coreml:qwen2.5-0.5b-instruct-onnx": "ollama:qwen2.5:7b",
        "apple-coreml:qwen3.5-4b-onnx-q4f16": "ollama:qwen2.5:7b",
    }
    if not model:
        return None
    return mapping.get(model)


def resolve_repair_model(
    *,
    base_model: str | None,
    attempt: int,
    override_model: str = "",
) -> str | None:
    if attempt <= 1:
        return base_model

    candidate = override_model or default_repair_fallback_model(base_model) or base_model
    if not override_model and model_provider_name(candidate) != model_provider_name(base_model):
        candidate = base_model
    if is_cross_apple_runtime_switch(base_model, candidate):
        from core.generation.provider import ProviderError

        raise ProviderError(
            "ANE_REPAIR_FALLBACK_MODEL ne peut pas viser un autre modèle apple-coreml pendant un même smoke. "
            "Relancer le runtime Apple sur le modèle cible ou utiliser un fallback non-Apple."
        )
    return candidate
