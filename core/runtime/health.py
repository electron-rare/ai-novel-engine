from __future__ import annotations

import json
import time
from urllib import error, request

from core.runtime.models import RuntimeHealth, RuntimeProfile


def probe_runtime_health(
    profile: RuntimeProfile,
    *,
    opener=request.urlopen,
    json_fetcher=None,
    health_fetcher=None,
) -> RuntimeHealth:
    url = _health_url(profile.base_url)
    try:
        if health_fetcher is not None:
            payload = health_fetcher(url, profile.timeout)
        else:
            with opener(url, timeout=profile.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
    except (OSError, error.URLError, error.HTTPError, json.JSONDecodeError) as exc:
        return RuntimeHealth(ok=False, url=url, detail=str(exc))

    if not isinstance(payload, dict):
        return RuntimeHealth(ok=False, url=url, detail="Réponse health non exploitable.")

    active_model = None
    for key in ("model", "active_model", "model_id"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            active_model = value.strip()
            break

    status = payload.get("status")
    available_models = None
    detail = None
    if json_fetcher is not None:
        models_url = runtime_models_url(profile.base_url)
        try:
            models_payload = json_fetcher(models_url, profile.timeout)
        except (OSError, error.URLError, error.HTTPError, json.JSONDecodeError):
            detail = "Runtime joignable mais catalogue modeles indisponible."
        else:
            available_models = extract_runtime_model_ids(models_payload)
            if active_model is None and len(available_models) == 1:
                active_model = available_models[0]

    return RuntimeHealth(
        ok=True,
        url=url,
        status=str(status).strip() if status is not None else None,
        active_model=active_model,
        available_models=available_models,
        detail=detail,
    )


def runtime_model_ids(
    profile: RuntimeProfile,
    *,
    json_fetcher,
) -> set[str]:
    payload = json_fetcher(runtime_models_url(profile.base_url), profile.timeout)
    return set(extract_runtime_model_ids(payload))


def current_apple_model(
    base_url: str,
    *,
    json_fetcher,
    timeout: float = 10.0,
) -> str | None:
    try:
        payload = json_fetcher(f"{base_url.rstrip('/')}/models", timeout)
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    model_ids = extract_runtime_model_ids(payload)
    return model_ids[0] if model_ids else None


def wait_for_expected_apple_model(
    base_url: str,
    target_model: str,
    *,
    json_fetcher,
    timeout_seconds: float,
    poll_interval_seconds: float,
    sleeper=time.sleep,
    monotonic=time.monotonic,
) -> str | None:
    deadline = monotonic() + max(timeout_seconds, 0.0)
    poll_interval = max(poll_interval_seconds, 0.1)
    last_seen = current_apple_model(base_url, json_fetcher=json_fetcher)
    if last_seen == target_model or timeout_seconds <= 0:
        return last_seen
    while monotonic() < deadline:
        sleeper(poll_interval)
        last_seen = current_apple_model(base_url, json_fetcher=json_fetcher)
        if last_seen == target_model:
            return last_seen
    return last_seen


def _health_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/health"):
        return base
    if base.endswith("/v1"):
        base = base[:-3].rstrip("/")
    return f"{base}/health"


def runtime_models_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1/chat/completions"):
        return f"{base[:-len('/chat/completions')]}/models"
    if base.endswith("/chat/completions"):
        return f"{base[:-len('/chat/completions')]}/models"
    if base.endswith("/v1"):
        return f"{base}/models"
    return f"{base}/v1/models"


def extract_runtime_model_ids(payload: object) -> list[str]:
    model_ids: list[str] = []
    if isinstance(payload, list):
        model_ids.extend(str(item) for item in payload)
    if isinstance(payload, dict):
        if isinstance(payload.get("data"), list):
            for item in payload["data"]:
                if isinstance(item, dict):
                    for key in ("id", "name", "model"):
                        value = str(item.get(key, "")).strip()
                        if value:
                            model_ids.append(value)
                    aliases = item.get("aliases")
                    if isinstance(aliases, list):
                        model_ids.extend(str(alias).strip() for alias in aliases if str(alias).strip())
                else:
                    model_ids.append(str(item))
        if isinstance(payload.get("models"), list):
            for item in payload["models"]:
                if isinstance(item, dict):
                    for key in ("id", "name", "model"):
                        value = str(item.get(key, "")).strip()
                        if value:
                            model_ids.append(value)
                else:
                    model_ids.append(str(item))
    return [item for item in model_ids if item]
