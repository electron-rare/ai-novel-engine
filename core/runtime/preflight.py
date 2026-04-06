from __future__ import annotations

from dataclasses import dataclass
import json
import time
from urllib import error, request


@dataclass(frozen=True)
class RuntimePreflightResult:
    args: list[str]
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float


def ollama_base_url(tags_url: str) -> str:
    normalized = tags_url.rstrip("/")
    suffix = "/api/tags"
    if normalized.endswith(suffix):
        return normalized[: -len(suffix)]
    return normalized


def run_ollama_native_preflight(
    *,
    model: str,
    tags_url: str,
    timeout_seconds: float,
    opener=request.urlopen,
    monotonic=time.monotonic,
) -> RuntimePreflightResult:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Respond with exactly: ollama native preflight ok"}],
        "stream": False,
        "options": {
            "temperature": 0,
            "num_predict": 16,
        },
    }
    body = json.dumps(payload).encode("utf-8")
    started = monotonic()
    try:
        req = request.Request(
            f"{ollama_base_url(tags_url)}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with opener(req, timeout=timeout_seconds) as response:
            raw_payload = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return RuntimePreflightResult(
            args=["ollama-native-preflight", model],
            returncode=1,
            stdout="",
            stderr=f"HTTP {exc.code} {exc.reason}\n{detail}".strip(),
            duration_seconds=monotonic() - started,
        )
    except (OSError, error.URLError, TimeoutError) as exc:
        return RuntimePreflightResult(
            args=["ollama-native-preflight", model],
            returncode=1,
            stdout="",
            stderr=f"{type(exc).__name__}: {exc}",
            duration_seconds=monotonic() - started,
        )

    try:
        parsed = json.loads(raw_payload)
    except json.JSONDecodeError:
        parsed = {"raw": raw_payload}
    preview = {
        "model": parsed.get("model"),
        "content": (parsed.get("message") or {}).get("content", ""),
        "done_reason": parsed.get("done_reason"),
    }
    return RuntimePreflightResult(
        args=["ollama-native-preflight", model],
        returncode=0,
        stdout=json.dumps(preview, ensure_ascii=False, indent=2),
        stderr="",
        duration_seconds=monotonic() - started,
    )
