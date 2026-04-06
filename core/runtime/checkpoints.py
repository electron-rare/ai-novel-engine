from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class RuntimeManualAction:
    reason: str
    args: list[str]


def checkpoint_manual_action_for_model(
    *,
    model: str,
    core_health_ok: bool,
    ollama_runtime: str,
    ollama_openai_runtime_ready: bool,
    ollama_openai_base_url: str,
    apple_model_active: str | None,
    repo_root: str,
    state_path: str,
    ane_script_path: str,
) -> RuntimeManualAction | None:
    if not core_health_ok:
        return RuntimeManualAction(
            reason="Le core mascarade ne répond pas correctement.",
            args=[
                "bash",
                "scripts/prepare_runtime_step.sh",
                "--restart",
                "core",
                "--resume-state",
                state_path,
                "--ane-script",
                ane_script_path,
            ],
        )

    if model.startswith("ollama:") and ollama_runtime == "openai_compatible" and not ollama_openai_runtime_ready:
        host, port = host_port_from_base_url(ollama_openai_base_url)
        return RuntimeManualAction(
            reason=(
                "Le runtime OpenAI-compatible attendu pour "
                f"`{model}` ne publie pas encore ce modele sur `{ollama_openai_base_url}`."
            ),
            args=[
                "bash",
                f"{repo_root}/scripts/prepare_llama_cpp_runtime.sh",
                "--model",
                model,
                "--host",
                host,
                "--port",
                str(port),
                "--resume-state",
                state_path,
                "--ane-script",
                ane_script_path,
            ],
        )

    if model.startswith("apple-coreml:"):
        target_model = model.split(":", 1)[1]
        if apple_model_active != target_model:
            return RuntimeManualAction(
                reason=f"Le runtime Apple sert `{apple_model_active or 'aucun modèle'}` au lieu de `{target_model}`.",
                args=[
                    "bash",
                    "scripts/prepare_runtime_step.sh",
                    "--apple-model",
                    target_model,
                    "--resume-state",
                    state_path,
                    "--ane-script",
                    ane_script_path,
                ],
            )

    return None


def host_port_from_base_url(base_url: str) -> tuple[str, int]:
    candidate = base_url.strip()
    if "://" not in candidate:
        candidate = f"http://{candidate}"
    parsed = urlparse(candidate)
    host = parsed.hostname or "127.0.0.1"
    if parsed.port is not None:
        return host, parsed.port
    return host, 443 if parsed.scheme == "https" else 80
