from __future__ import annotations

import re
from urllib.parse import urlparse


PROFILE_OPENAI_COMPATIBLE_GENERIC = "openai_compatible_generic"
PROFILE_OPENAI_PROBE = "openai_probe"
PROFILE_MASCARADE_LOCAL = "mascarade_local"
PROFILE_MASCARADE_REMOTE_PREFIX = "mascarade_remote"
PROFILE_APPLE_COREML_SINGLE_MODEL = "apple_coreml_single_model"
PROFILE_OLLAMA_NATIVE = "ollama_native"
PROFILE_OLLAMA_OPENAI_COMPATIBLE = "ollama_openai_compatible"
PROFILE_LLAMA_CPP_LOCAL = "llama_cpp_local"


def runtime_profile_name_for_model(model: str, *, ollama_runtime: str = "openai_compatible") -> str:
    if model.startswith("apple-coreml:"):
        return PROFILE_APPLE_COREML_SINGLE_MODEL
    if model.startswith("ollama:"):
        if ollama_runtime == "native":
            return PROFILE_OLLAMA_NATIVE
        return PROFILE_OLLAMA_OPENAI_COMPATIBLE
    return PROFILE_OPENAI_COMPATIBLE_GENERIC


def runtime_probe_name(kind: str, *, base_url: str | None = None, remote_name: str | None = None) -> str:
    if kind == "core":
        return PROFILE_MASCARADE_LOCAL
    if kind == "apple":
        return PROFILE_APPLE_COREML_SINGLE_MODEL
    if kind == "ollama_openai":
        return PROFILE_LLAMA_CPP_LOCAL
    if kind == "remote":
        suffix = remote_name or _remote_suffix_from_base_url(base_url or "")
        if suffix:
            return f"{PROFILE_MASCARADE_REMOTE_PREFIX}_{suffix}"
        return PROFILE_MASCARADE_REMOTE_PREFIX
    return PROFILE_OPENAI_PROBE


def _remote_suffix_from_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    host = (parsed.hostname or "").strip().lower()
    if not host:
        return ""
    host = re.sub(r"[^a-z0-9]+", "_", host).strip("_")
    return host
