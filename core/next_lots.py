from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import inspect
import json
import os
from pathlib import Path
import subprocess
import time
import tomllib
import tempfile
from typing import Any, Callable
from urllib import error, request

from core.chapters import ChapterId
from core.runtime.checkpoints import checkpoint_manual_action_for_model, host_port_from_base_url
from core.runtime.orchestration import (
    build_runtime_execution_plan,
    collect_checkpoint_runtime_signals,
    missing_ollama_models,
    read_current_apple_model,
    runtime_timeout_for_model,
)
from core.runtime.preflight import run_ollama_native_preflight
from core.tracking_sync import TrackingPaths, build_tracking_sync_context, sync_tracking, write_report_summary


class NextLotsError(RuntimeError):
    """Raised when the orchestration flow cannot continue automatically."""

@dataclass(frozen=True)
class Manifest:
    repo_root: Path
    manifest_path: Path
    tracking: TrackingPaths
    core_base_url: str
    apple_runtime_url: str
    ollama_tags_url: str
    ollama_runtime: str
    ollama_openai_base_url: str
    apple_model_ready_timeout_seconds: float
    apple_model_poll_interval_seconds: float
    smoke_chapter: str
    smoke_intention: str
    smoke_timeout_seconds: int
    preset_env: dict[str, str]
    required_apple_models: list[str]
    required_ollama_models: list[str]
    priority_models: list[str]
    baseline_models: list[str]
    preflight_only_models: list[str]
    french_models: list[str]
    prompt_profiles: dict[str, str]
    next_code_lot: str

    @classmethod
    def load(cls, repo_root: Path, manifest_path: Path) -> "Manifest":
        payload = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
        paths = payload["paths"]
        smoke = payload["smoke"]
        preset = payload["preset"]
        tracking = payload["tracking"]
        lots = payload["lots"]
        ensure_models = payload["ensure_models"]
        ollama_runtime = str(paths.get("ollama_runtime", "native")).strip() or "native"
        if ollama_runtime not in {"native", "openai_compatible"}:
            raise NextLotsError(
                "paths.ollama_runtime doit valoir 'native' ou 'openai_compatible'."
            )

        mascarade_repo = Path(paths["mascarade_repo"]).expanduser()
        return cls(
            repo_root=repo_root,
            manifest_path=manifest_path,
            tracking=TrackingPaths(
                ane_todo_active=repo_root / tracking["ane"]["todo_active"],
                ane_todo_done=repo_root / tracking["ane"]["todo_done"],
                ane_plan=repo_root / tracking["ane"]["plan"],
                ane_comparison=repo_root / tracking["ane"]["comparison"],
                ane_readme=repo_root / tracking["ane"]["readme"],
                ane_runbook=repo_root / tracking["ane"]["runbook"],
                mascarade_repo=mascarade_repo,
                mascarade_todo=mascarade_repo / tracking["mascarade"]["todo"],
                mascarade_plan=mascarade_repo / tracking["mascarade"]["plan"],
                mascarade_readme=mascarade_repo / tracking["mascarade"]["readme"],
                mascarade_runbook=mascarade_repo / tracking["mascarade"]["runbook"],
            ),
            core_base_url=str(paths["core_base_url"]).rstrip("/"),
            apple_runtime_url=str(paths["apple_runtime_url"]).rstrip("/"),
            ollama_tags_url=str(paths["ollama_tags_url"]).rstrip("/"),
            ollama_runtime=ollama_runtime,
            ollama_openai_base_url=str(
                paths.get("ollama_openai_base_url", paths["core_base_url"])
            ).rstrip("/"),
            apple_model_ready_timeout_seconds=float(paths.get("apple_model_ready_timeout_seconds", 30)),
            apple_model_poll_interval_seconds=float(paths.get("apple_model_poll_interval_seconds", 2)),
            smoke_chapter=str(smoke["chapter"]),
            smoke_intention=str(smoke["intention"]),
            smoke_timeout_seconds=int(smoke["timeout_seconds"]),
            preset_env={str(key): str(value) for key, value in preset.items()},
            required_apple_models=[str(item) for item in ensure_models["apple_models"]],
            required_ollama_models=[str(item) for item in ensure_models["ollama_models"]],
            priority_models=[str(item) for item in lots["priority_models"]["models"]],
            baseline_models=[str(item) for item in lots["baselines"]["models"]],
            preflight_only_models=[str(item) for item in lots["preflight_only"]["models"]],
            french_models=[str(item) for item in lots.get("french_models", {}).get("models", [])],
            prompt_profiles={str(k): str(v) for k, v in payload.get("prompt_profiles", {}).items()},
            next_code_lot=str(payload["next_actions"]["rewrite_compaction"]),
        )


@dataclass
class CommandResult:
    args: list[str]
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float


CommandRunner = Callable[..., CommandResult]
JsonFetcher = Callable[[str, float], Any]


@dataclass
class ModelRunResult:
    model: str
    category: str
    classification: str = "pending"
    preflight_ok: bool | None = None
    preflight_duration_seconds: float | None = None
    smoke_attempted: bool = False
    smoke_duration_seconds: float | None = None
    status: str | None = None
    accepted: bool = False
    failed_stage: str | None = None
    quality_blockers: list[str] = field(default_factory=list)
    retry_stages: list[str] = field(default_factory=list)
    repair_attempts: int = 0
    repair_models: list[str] = field(default_factory=list)
    draft_path: str | None = None
    gate_path: str | None = None
    meta_path: str | None = None
    manuscript_path: str | None = None
    notes: list[str] = field(default_factory=list)
    preflight_log: str | None = None
    smoke_log: str | None = None
    workspace: str | None = None
    apple_model_active: str | None = None
    completed_stages: list[str] = field(default_factory=list)

    def reached_gate(self) -> bool:
        return "gate" in self.completed_stages or (self.failed_stage == "gate")


@dataclass
class RunState:
    version: int
    manifest_path: str
    report_dir: str
    state_path: str
    lot: str
    started_at: str
    updated_at: str
    step_index: int
    model_index: int
    steps: list[dict[str, Any]]
    results: list[dict[str, Any]]
    notes: list[str]
    pending_manual_action: dict[str, Any] | None
    next_recommended_lot: str

    @classmethod
    def new(cls, manifest: Manifest, lot: str, report_dir: Path, state_path: Path, steps: list[dict[str, Any]]) -> "RunState":
        now = _timestamp()
        return cls(
            version=1,
            manifest_path=str(manifest.manifest_path),
            report_dir=str(report_dir),
            state_path=str(state_path),
            lot=lot,
            started_at=now,
            updated_at=now,
            step_index=0,
            model_index=0,
            steps=steps,
            results=[],
            notes=[],
            pending_manual_action=None,
            next_recommended_lot=manifest.next_code_lot,
        )

    @classmethod
    def load(cls, path: Path) -> "RunState":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(**payload)

    def dump(self, path: Path | None = None) -> None:
        target = path or Path(self.state_path)
        self.updated_at = _timestamp()
        target.parent.mkdir(parents=True, exist_ok=True)
        rendered = json.dumps(asdict(self), ensure_ascii=False, indent=2) + "\n"
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target.parent,
            delete=False,
            suffix=".tmp",
        ) as handle:
            handle.write(rendered)
            temp_path = Path(handle.name)
        temp_path.replace(target)

    def append_result(self, result: ModelRunResult) -> None:
        self.results.append(asdict(result))
        self.updated_at = _timestamp()

    def typed_results(self) -> list[ModelRunResult]:
        return [ModelRunResult(**payload) for payload in self.results]


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _default_command_runner(
    args: list[str],
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout_seconds: float | None = None,
) -> CommandResult:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    started = time.monotonic()
    try:
        completed = subprocess.run(
            args,
            cwd=str(cwd),
            env=merged_env,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout.decode("utf-8", errors="replace") if exc.stdout else "")
        stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr.decode("utf-8", errors="replace") if exc.stderr else "")
        detail = f"Timed out after {timeout_seconds:.1f}s." if timeout_seconds is not None else "Timed out."
        stderr = f"{stderr}\n{detail}".strip()
        return CommandResult(
            args=args,
            returncode=124,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=time.monotonic() - started,
        )
    return CommandResult(
        args=args,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        duration_seconds=time.monotonic() - started,
    )


def _default_json_fetcher(url: str, timeout: float) -> Any:
    with request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


class NextLotsRunner:
    def __init__(
        self,
        manifest: Manifest,
        *,
        command_runner: CommandRunner = _default_command_runner,
        json_fetcher: JsonFetcher = _default_json_fetcher,
    ) -> None:
        self.manifest = manifest
        self.command_runner = command_runner
        self.json_fetcher = json_fetcher
        self._command_runner_supports_timeout = len(inspect.signature(command_runner).parameters) >= 4

    def run(
        self,
        *,
        lot: str,
        resume_state: Path | None = None,
        dry_run: bool = False,
        report_only: bool = False,
    ) -> int:
        state_path = self.manifest.repo_root / "automation" / "state" / "next_lots_state.json"
        if resume_state is not None:
            state = RunState.load(resume_state)
        else:
            report_dir = self._new_report_dir()
            state = RunState.new(
                self.manifest,
                lot=lot,
                report_dir=report_dir,
                state_path=state_path,
                steps=self._steps_for_lot(lot),
            )
            state.dump(state_path)

        if report_only:
            sync_tracking(
                build_tracking_sync_context(
                    self.manifest.repo_root,
                    next_code_lot=self.manifest.next_code_lot,
                    tracking=self.manifest.tracking,
                ),
                state,
                dry_run=dry_run,
            )
            return 0

        while state.step_index < len(state.steps):
            step = state.steps[state.step_index]
            step_type = str(step["type"])
            if step_type == "ensure_models":
                print("==> lot ensure_models")
                self._run_ensure_models(state, dry_run=dry_run)
                state.step_index += 1
                state.model_index = 0
                state.dump()
                continue
            if step_type == "models":
                print(f"==> lot {step['name']}")
                exit_code = self._run_model_step(state, step, dry_run=dry_run)
                state.dump()
                if exit_code is not None:
                    sync_tracking(
                        build_tracking_sync_context(
                            self.manifest.repo_root,
                            next_code_lot=self.manifest.next_code_lot,
                            tracking=self.manifest.tracking,
                        ),
                        state,
                        dry_run=dry_run,
                    )
                    return exit_code
                state.step_index += 1
                state.model_index = 0
                state.dump()
                continue
            if step_type == "tracking_sync":
                print("==> lot tracking_sync")
                sync_tracking(
                    build_tracking_sync_context(
                        self.manifest.repo_root,
                        next_code_lot=self.manifest.next_code_lot,
                        tracking=self.manifest.tracking,
                    ),
                    state,
                    dry_run=dry_run,
                )
                state.step_index += 1
                state.model_index = 0
                state.dump()
                continue
            raise NextLotsError(f"Type de lot non supporté: {step_type}")

        write_report_summary(state)
        return 0

    def _steps_for_lot(self, lot: str) -> list[dict[str, Any]]:
        if lot == "ensure_models":
            return [{"type": "ensure_models"}]
        if lot == "runtime_preflight":
            queue = [*self.manifest.priority_models, *self.manifest.baseline_models]
            return [{"type": "models", "name": "runtime_preflight", "models": queue, "preflight_only": True}]
        if lot == "priority_models":
            return [
                {"type": "models", "name": "priority_models", "models": self.manifest.priority_models, "preflight_only": False},
                {"type": "tracking_sync"},
            ]
        if lot == "baselines":
            return [
                {"type": "models", "name": "baselines", "models": self.manifest.baseline_models, "preflight_only": False},
                {"type": "models", "name": "preflight_only", "models": self.manifest.preflight_only_models, "preflight_only": True},
                {"type": "tracking_sync"},
            ]
        if lot == "french_models":
            return [
                {"type": "models", "name": "french_models", "models": self.manifest.french_models, "preflight_only": False},
                {"type": "tracking_sync"},
            ]
        if lot == "tracking_sync":
            return [{"type": "tracking_sync"}]
        if lot == "full":
            return [
                {"type": "ensure_models"},
                {"type": "models", "name": "priority_models", "models": self.manifest.priority_models, "preflight_only": False},
                {"type": "models", "name": "baselines", "models": self.manifest.baseline_models, "preflight_only": False},
                {"type": "models", "name": "preflight_only", "models": self.manifest.preflight_only_models, "preflight_only": True},
                {"type": "tracking_sync"},
            ]
        raise NextLotsError(f"Lot inconnu: {lot}")

    def _new_report_dir(self) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        report_dir = self.manifest.repo_root / "automation" / "reports" / stamp
        report_dir.mkdir(parents=True, exist_ok=True)
        return report_dir

    def _run_ensure_models(self, state: RunState, *, dry_run: bool) -> None:
        if dry_run:
            state.notes.append("Dry-run: ensure_models non exécuté.")
            return
        args = ["bash", "scripts/ensure_apple_models.sh"]
        result = self._invoke_command(args, self.manifest.tracking.mascarade_repo, timeout_seconds=900)
        log_path = Path(state.report_dir) / "ensure_models.log"
        log_path.write_text(_command_log(result), encoding="utf-8")
        if result.returncode != 0:
            raise NextLotsError("ensure_models a échoué.")
        missing = self._missing_ollama_models()
        if missing:
            state.notes.append(
                "Modèles Ollama manquants: " + ", ".join(missing) + ". Lancer manuellement `ollama pull` sur ces modèles."
            )

    def _missing_ollama_models(self) -> list[str]:
        return missing_ollama_models(
            self.manifest.required_ollama_models,
            tags_url=self.manifest.ollama_tags_url,
            json_fetcher=self.json_fetcher,
        )

    def _run_model_step(self, state: RunState, step: dict[str, Any], *, dry_run: bool) -> int | None:
        models = [str(item) for item in step["models"]]
        preflight_only = bool(step.get("preflight_only", False))
        for index in range(state.model_index, len(models)):
            state.model_index = index
            model = models[index]
            category = str(step["name"])
            state.notes = [f"Modele en cours: {model}"]
            state.dump()
            print(f"--> {model}")
            if dry_run:
                state.append_result(
                    ModelRunResult(
                        model=model,
                        category=category,
                        classification="dry_run",
                        notes=["Dry-run: aucun preflight ni smoke exécuté."],
                    )
                )
                continue
            checkpoint = self._checkpoint_if_runtime_manual_step_needed(state, model)
            if checkpoint is not None:
                print(f"checkpoint manuel: {checkpoint['reason']}")
                print(f"commande: {checkpoint['command']}")
                state.pending_manual_action = checkpoint
                state.notes = [f"Checkpoint manuel requis pour: {model}"]
                write_report_summary(state)
                return 3
            state.pending_manual_action = None
            result = self._run_model(model, category=category, preflight_only=preflight_only, report_dir=Path(state.report_dir))
            state.notes = [f"Dernier modele traite: {model} -> {result.classification}"]
            state.append_result(result)
        return None

    def _checkpoint_if_runtime_manual_step_needed(self, state: RunState, model: str) -> dict[str, Any] | None:
        signals = collect_checkpoint_runtime_signals(
            model,
            core_base_url=self.manifest.core_base_url,
            apple_runtime_url=self.manifest.apple_runtime_url,
            apple_model_ready_timeout_seconds=self.manifest.apple_model_ready_timeout_seconds,
            apple_model_poll_interval_seconds=self.manifest.apple_model_poll_interval_seconds,
            ollama_runtime=self.manifest.ollama_runtime,
            ollama_openai_base_url=self.manifest.ollama_openai_base_url,
            json_fetcher=self.json_fetcher,
        )
        action = checkpoint_manual_action_for_model(
            model=model,
            core_health_ok=signals.core_health_ok,
            ollama_runtime=self.manifest.ollama_runtime,
            ollama_openai_runtime_ready=signals.ollama_openai_runtime_ready,
            ollama_openai_base_url=self.manifest.ollama_openai_base_url,
            apple_model_active=signals.apple_model_active,
            repo_root=str(self.manifest.repo_root),
            state_path=state.state_path,
            ane_script_path=str(self.manifest.repo_root / "scripts" / "run_next_lots.py"),
        )
        if action is None:
            return None
        return self._build_manual_action(state, args=action.args, reason=action.reason)

    def _build_manual_action(self, state: RunState, *, args: list[str], reason: str) -> dict[str, Any]:
        result = self._invoke_command(args, self.manifest.tracking.mascarade_repo, timeout_seconds=300)
        log_path = Path(state.report_dir) / f"manual_action_{len(state.results):02d}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(_command_log(result), encoding="utf-8")
        return {
            "reason": reason,
            "command": " ".join(args),
            "log_path": str(log_path),
            "resume_state": state.state_path,
        }

    def _current_apple_model(self) -> str | None:
        return read_current_apple_model(
            self.manifest.apple_runtime_url,
            json_fetcher=self.json_fetcher,
        )

    def _ollama_base_url(self) -> str:
        tags_url = self.manifest.ollama_tags_url.rstrip("/")
        suffix = "/api/tags"
        if tags_url.endswith(suffix):
            return tags_url[: -len(suffix)]
        return tags_url

    def _host_port_from_base_url(self, base_url: str) -> tuple[str, int]:
        return host_port_from_base_url(base_url)

    def _run_ollama_native_preflight(self, model: str) -> CommandResult:
        timeout_seconds = min(45.0, float(self._timeout_for_model(f"ollama:{model}")))
        result = run_ollama_native_preflight(
            model=model,
            tags_url=self.manifest.ollama_tags_url,
            timeout_seconds=timeout_seconds,
            opener=request.urlopen,
        )
        return CommandResult(
            args=result.args,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            duration_seconds=result.duration_seconds,
        )

    def _invoke_command(
        self,
        args: list[str],
        cwd: Path,
        *,
        env: dict[str, str] | None = None,
        timeout_seconds: float | None = None,
    ) -> CommandResult:
        if self._command_runner_supports_timeout:
            return self.command_runner(args, cwd, env, timeout_seconds)
        return self.command_runner(args, cwd, env)

    def _run_model(self, model: str, *, category: str, preflight_only: bool, report_dir: Path) -> ModelRunResult:
        result = ModelRunResult(model=model, category=category, apple_model_active=self._current_apple_model())
        model_slug = _slugify(model)
        runtime_plan = build_runtime_execution_plan(
            model,
            core_base_url=self.manifest.core_base_url,
            ollama_runtime=self.manifest.ollama_runtime,
            ollama_openai_base_url=self.manifest.ollama_openai_base_url,
            smoke_timeout_seconds=self.manifest.smoke_timeout_seconds,
        )
        if runtime_plan.requires_native_ollama_preflight:
            native_preflight = self._run_ollama_native_preflight(model.split(":", 1)[1])
            if native_preflight.returncode != 0:
                result.preflight_duration_seconds = native_preflight.duration_seconds
                native_log = report_dir / f"{model_slug}_ollama_native_preflight.log"
                native_log.write_text(_command_log(native_preflight), encoding="utf-8")
                result.preflight_log = str(native_log)
                result.preflight_ok = False
                result.classification = "provider_failed"
                result.status = "ollama_runtime_unhealthy"
                result.notes.append("Le preflight Ollama natif a échoué.")
                hint = _runtime_error_hint(native_preflight.stderr)
                if hint:
                    result.notes.append(hint)
                return result
        preflight_args = [
            "bash",
            "scripts/smoke_openai_compat_ane.sh",
            "--url",
            runtime_plan.openai_base_url,
            "--model",
            model,
            "--timeout",
            str(runtime_plan.timeout_seconds),
        ]
        preflight = self._invoke_command(
            preflight_args,
            self.manifest.tracking.mascarade_repo,
            timeout_seconds=float(runtime_plan.timeout_seconds + 30),
        )
        result.preflight_duration_seconds = preflight.duration_seconds
        preflight_log = report_dir / f"{model_slug}_preflight.log"
        preflight_log.write_text(_command_log(preflight), encoding="utf-8")
        result.preflight_log = str(preflight_log)
        result.preflight_ok = preflight.returncode == 0
        if not result.preflight_ok:
            result.classification = "provider_failed"
            result.status = "preflight_failed"
            result.notes.append("Le preflight OpenAI-compatible a échoué.")
            return result
        if preflight_only:
            result.classification = "preflight_only"
            result.status = "preflight_only"
            result.notes.append("Smoke complet volontairement sauté pour ce modèle.")
            return result

        workspace = report_dir / "workspaces" / model_slug
        workspace.parent.mkdir(parents=True, exist_ok=True)
        smoke_args = [
            "bash",
            "scripts/smoke_local_generation.sh",
            "--base-url",
            runtime_plan.openai_base_url,
            "--model",
            model,
            "--chapter",
            self.manifest.smoke_chapter,
            "--workspace",
            str(workspace),
            "--timeout",
            str(runtime_plan.timeout_seconds),
            "--intention",
            self.manifest.smoke_intention,
            "--approve",
        ]
        smoke_env = dict(self.manifest.preset_env)
        profile = self.manifest.prompt_profiles.get(model)
        if profile:
            smoke_env["ANE_PROMPT_PROFILE"] = profile
        smoke = self._invoke_command(
            smoke_args,
            self.manifest.repo_root,
            env=smoke_env,
            timeout_seconds=float(runtime_plan.timeout_seconds * 4),
        )
        result.smoke_attempted = True
        result.smoke_duration_seconds = smoke.duration_seconds
        smoke_log = report_dir / f"{model_slug}_smoke.log"
        smoke_log.write_text(_command_log(smoke), encoding="utf-8")
        result.smoke_log = str(smoke_log)
        result.workspace = str(workspace)

        chapter = ChapterId.parse(self.manifest.smoke_chapter)
        meta_path = workspace / "brouillons" / "chapitres" / chapter.slug / "meta.json"
        if not meta_path.exists():
            result.classification = "provider_failed"
            result.status = "missing_meta"
            result.notes.append("Le smoke n'a pas produit de meta.json exploitable.")
            return result

        payload = json.loads(meta_path.read_text(encoding="utf-8"))
        result.meta_path = str(meta_path)
        result.status = str(payload.get("status", "")).strip() or None
        result.accepted = bool(payload.get("accepted", False))
        result.failed_stage = str(payload.get("failed_stage", "")).strip() or None
        result.quality_blockers = _string_list(payload.get("quality_blockers"))
        result.retry_stages = _string_list(payload.get("retry_stages"))
        result.repair_attempts = int(payload.get("repair_attempts", 0) or 0)
        result.repair_models = _string_list(payload.get("repair_models"))
        result.completed_stages = _string_list(payload.get("completed_stages"))
        artifacts = payload.get("artifacts", {})
        if isinstance(artifacts, dict):
            result.draft_path = _optional_string(artifacts.get("repair_latest")) or _optional_string(artifacts.get("draft_v2"))
            result.gate_path = _optional_string(artifacts.get("gate_v1"))
            result.manuscript_path = _optional_string(artifacts.get("manuscript"))

        if result.status == "accepted":
            result.classification = "accepted"
        elif result.status == "quality_blocked":
            result.classification = "quality_blocked"
        elif smoke.returncode == 0 and result.status == "rejected":
            result.classification = "provider_failed"
        else:
            result.classification = "provider_failed"
        return result

    def _timeout_for_model(self, model: str) -> int:
        return runtime_timeout_for_model(model, smoke_timeout_seconds=self.manifest.smoke_timeout_seconds)

def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _optional_string(value: object) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _runtime_error_hint(stderr: str) -> str | None:
    for raw_line in stderr.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        return line[:240]
    return None


def _slugify(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value).strip("_").lower()


def _command_log(result: CommandResult) -> str:
    return (
        f"$ {' '.join(result.args)}\n"
        f"returncode={result.returncode}\n"
        f"duration_seconds={result.duration_seconds:.2f}\n\n"
        f"STDOUT\n{result.stdout}\n\nSTDERR\n{result.stderr}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 scripts/run_next_lots.py")
    parser.add_argument("--manifest", default="automation/next_lots.toml")
    parser.add_argument("--lot", default="full", choices=["full", "ensure_models", "runtime_preflight", "priority_models", "baselines", "french_models", "tracking_sync"])
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    return parser


def main(argv: list[str] | None = None, repo_root: Path | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = repo_root or Path.cwd()
    manifest = Manifest.load(root, root / args.manifest)
    runner = NextLotsRunner(manifest)
    return runner.run(
        lot=args.lot,
        resume_state=args.resume,
        dry_run=args.dry_run,
        report_only=args.report_only,
    )


if __name__ == "__main__":
    raise SystemExit(main())
