from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import time
import tomllib
from typing import Any, Callable, Iterable
from urllib import error, request

from core.chapters import ChapterId
from core.project.loader import ProjectState


AUTO_SYNC_TODO_ACTIVE = "ANE-TODO-ACTIVE"
AUTO_SYNC_TODO_DONE = "ANE-TODO-DONE"
AUTO_SYNC_PLAN = "ANE-PLAN"
AUTO_SYNC_COMPARISON = "ANE-COMPARISON"
AUTO_SYNC_README = "ANE-README"
AUTO_SYNC_RUNBOOK = "ANE-RUNBOOK"
AUTO_SYNC_MASCARADE_TODO = "MASCARADE-TODO"
AUTO_SYNC_MASCARADE_PLAN = "MASCARADE-PLAN"
AUTO_SYNC_MASCARADE_README = "MASCARADE-README"
AUTO_SYNC_MASCARADE_RUNBOOK = "MASCARADE-RUNBOOK"


class NextLotsError(RuntimeError):
    """Raised when the orchestration flow cannot continue automatically."""


@dataclass(frozen=True)
class TrackingPaths:
    ane_todo_active: Path
    ane_todo_done: Path
    ane_plan: Path
    ane_comparison: Path
    ane_readme: Path
    ane_runbook: Path
    mascarade_repo: Path
    mascarade_todo: Path
    mascarade_plan: Path
    mascarade_readme: Path
    mascarade_runbook: Path


@dataclass(frozen=True)
class Manifest:
    repo_root: Path
    manifest_path: Path
    tracking: TrackingPaths
    core_base_url: str
    apple_runtime_url: str
    ollama_tags_url: str
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
            next_code_lot=str(payload["next_actions"]["rewrite_compaction"]),
        )


@dataclass
class CommandResult:
    args: list[str]
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float


CommandRunner = Callable[[list[str], Path, dict[str, str] | None], CommandResult]
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
        target.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def append_result(self, result: ModelRunResult) -> None:
        self.results.append(asdict(result))
        self.updated_at = _timestamp()

    def typed_results(self) -> list[ModelRunResult]:
        return [ModelRunResult(**payload) for payload in self.results]


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _default_command_runner(args: list[str], cwd: Path, env: dict[str, str] | None = None) -> CommandResult:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    started = time.monotonic()
    completed = subprocess.run(
        args,
        cwd=str(cwd),
        env=merged_env,
        text=True,
        capture_output=True,
        check=False,
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


def _auto_markers(name: str) -> tuple[str, str]:
    return (
        f"<!-- AUTO-SYNC:{name}:START -->",
        f"<!-- AUTO-SYNC:{name}:END -->",
    )


def replace_auto_section(path: Path, marker_name: str, heading: str, body: str) -> None:
    start_marker, end_marker = _auto_markers(marker_name)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    section = f"{heading}\n{start_marker}\n{body.rstrip()}\n{end_marker}\n"
    if start_marker in text and end_marker in text:
        start = text.index(start_marker)
        end = text.index(end_marker) + len(end_marker)
        replacement_start = text.rfind("\n", 0, start)
        if replacement_start == -1:
            replacement_start = 0
        else:
            replacement_start += 1
        new_text = f"{text[:replacement_start]}{section}{text[end:].lstrip()}"
    else:
        suffix = "\n" if text.endswith("\n") else "\n\n"
        new_text = f"{text}{suffix}{section}"
    path.write_text(new_text, encoding="utf-8")


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
            self._sync_tracking(state, dry_run=dry_run)
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
                    self._sync_tracking(state, dry_run=dry_run)
                    return exit_code
                state.step_index += 1
                state.model_index = 0
                state.dump()
                continue
            if step_type == "tracking_sync":
                print("==> lot tracking_sync")
                self._sync_tracking(state, dry_run=dry_run)
                state.step_index += 1
                state.model_index = 0
                state.dump()
                continue
            raise NextLotsError(f"Type de lot non supporté: {step_type}")

        self._write_report_summary(state)
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
        result = self.command_runner(args, self.manifest.tracking.mascarade_repo)
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
        try:
            payload = self.json_fetcher(self.manifest.ollama_tags_url, 10.0)
        except Exception:
            return []
        models = payload.get("models") if isinstance(payload, dict) else None
        if not isinstance(models, list):
            return []
        names = {
            str(item.get("name", "")).strip()
            for item in models
            if isinstance(item, dict) and str(item.get("name", "")).strip()
        }
        return [model for model in self.manifest.required_ollama_models if model not in names]

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
                self._write_report_summary(state)
                return 3
            state.pending_manual_action = None
            result = self._run_model(model, category=category, preflight_only=preflight_only, report_dir=Path(state.report_dir))
            state.notes = [f"Dernier modele traite: {model} -> {result.classification}"]
            state.append_result(result)
        return None

    def _checkpoint_if_runtime_manual_step_needed(self, state: RunState, model: str) -> dict[str, Any] | None:
        if not self._core_health_ok():
            return self._build_manual_action(
                state,
                args=["bash", "scripts/prepare_runtime_step.sh", "--restart", "core", "--resume-state", state.state_path, "--ane-script", str(self.manifest.repo_root / "scripts" / "run_next_lots.py")],
                reason="Le core mascarade ne répond pas correctement.",
            )
        if not model.startswith("apple-coreml:"):
            return None
        target_model = model.split(":", 1)[1]
        apple_model = self._wait_for_expected_apple_model(target_model)
        if apple_model == target_model:
            return None
        args = [
            "bash",
            "scripts/prepare_runtime_step.sh",
            "--apple-model",
            target_model,
            "--resume-state",
            state.state_path,
            "--ane-script",
            str(self.manifest.repo_root / "scripts" / "run_next_lots.py"),
        ]
        return self._build_manual_action(
            state,
            args=args,
            reason=f"Le runtime Apple sert `{apple_model or 'aucun modèle'}` au lieu de `{target_model}`.",
        )

    def _build_manual_action(self, state: RunState, *, args: list[str], reason: str) -> dict[str, Any]:
        result = self.command_runner(args, self.manifest.tracking.mascarade_repo)
        log_path = Path(state.report_dir) / f"manual_action_{len(state.results):02d}.log"
        log_path.write_text(_command_log(result), encoding="utf-8")
        return {
            "reason": reason,
            "command": " ".join(args),
            "log_path": str(log_path),
            "resume_state": state.state_path,
        }

    def _core_health_ok(self) -> bool:
        try:
            payload = self.json_fetcher(f"{self.manifest.core_base_url}/health", 10.0)
        except Exception:
            return False
        return isinstance(payload, dict)

    def _current_apple_model(self) -> str | None:
        try:
            payload = self.json_fetcher(f"{self.manifest.apple_runtime_url}/models", 10.0)
        except Exception:
            return None
        if isinstance(payload, list) and payload:
            return str(payload[0]).strip() or None
        if isinstance(payload, dict):
            models = payload.get("models")
            if isinstance(models, list) and models:
                return str(models[0]).strip() or None
        return None

    def _wait_for_expected_apple_model(self, target_model: str) -> str | None:
        deadline = time.monotonic() + max(self.manifest.apple_model_ready_timeout_seconds, 0.0)
        poll_interval = max(self.manifest.apple_model_poll_interval_seconds, 0.1)
        last_seen = self._current_apple_model()
        if last_seen == target_model or self.manifest.apple_model_ready_timeout_seconds <= 0:
            return last_seen
        while time.monotonic() < deadline:
            time.sleep(poll_interval)
            last_seen = self._current_apple_model()
            if last_seen == target_model:
                return last_seen
        return last_seen

    def _run_model(self, model: str, *, category: str, preflight_only: bool, report_dir: Path) -> ModelRunResult:
        result = ModelRunResult(model=model, category=category, apple_model_active=self._current_apple_model())
        model_slug = _slugify(model)
        preflight_args = [
            "bash",
            "scripts/smoke_openai_compat_ane.sh",
            "--url",
            self.manifest.core_base_url,
            "--model",
            model,
            "--timeout",
            str(self._timeout_for_model(model)),
        ]
        preflight = self.command_runner(preflight_args, self.manifest.tracking.mascarade_repo)
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
            self.manifest.core_base_url,
            "--model",
            model,
            "--chapter",
            self.manifest.smoke_chapter,
            "--workspace",
            str(workspace),
            "--timeout",
            str(self.manifest.smoke_timeout_seconds),
            "--intention",
            self.manifest.smoke_intention,
            "--approve",
        ]
        smoke = self.command_runner(smoke_args, self.manifest.repo_root, env=self.manifest.preset_env)
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
        if model.startswith("apple-coreml:"):
            return max(600, self.manifest.smoke_timeout_seconds)
        return max(120, self.manifest.smoke_timeout_seconds)

    def _sync_tracking(self, state: RunState, *, dry_run: bool) -> None:
        if dry_run:
            self._write_report_summary(state)
            return
        typed_results = state.typed_results()
        project_state = ProjectState(self.manifest.repo_root).summary()
        summary = _build_summary(state, typed_results)
        comparison = _render_comparison_markdown(state, typed_results)
        active_next = _compute_next_lot_recommendation(typed_results, self.manifest.next_code_lot)

        replace_auto_section(
            self.manifest.tracking.ane_todo_active,
            AUTO_SYNC_TODO_ACTIVE,
            "## Auto-sync",
            _render_todo_active_sync(summary, active_next),
        )
        replace_auto_section(
            self.manifest.tracking.ane_todo_done,
            AUTO_SYNC_TODO_DONE,
            "## Auto-sync",
            _render_todo_done_sync(summary),
        )
        replace_auto_section(
            self.manifest.tracking.ane_plan,
            AUTO_SYNC_PLAN,
            "## Auto-sync",
            _render_plan_sync(summary, active_next),
        )
        replace_auto_section(
            self.manifest.tracking.ane_comparison,
            AUTO_SYNC_COMPARISON,
            "## Auto-sync",
            comparison,
        )
        replace_auto_section(
            self.manifest.tracking.ane_readme,
            AUTO_SYNC_README,
            "## Etat auto-synchronise",
            _render_readme_sync(summary, active_next),
        )
        replace_auto_section(
            self.manifest.tracking.ane_runbook,
            AUTO_SYNC_RUNBOOK,
            "## Etat auto-synchronise",
            _render_runbook_sync(summary, project_state, active_next),
        )
        replace_auto_section(
            self.manifest.tracking.mascarade_todo,
            AUTO_SYNC_MASCARADE_TODO,
            "## Auto-sync",
            _render_mascarade_todo_sync(summary, active_next),
        )
        replace_auto_section(
            self.manifest.tracking.mascarade_plan,
            AUTO_SYNC_MASCARADE_PLAN,
            "## Auto-sync",
            _render_mascarade_plan_sync(summary, active_next),
        )
        replace_auto_section(
            self.manifest.tracking.mascarade_readme,
            AUTO_SYNC_MASCARADE_README,
            "## Etat auto-synchronise",
            _render_mascarade_readme_sync(summary, active_next),
        )
        replace_auto_section(
            self.manifest.tracking.mascarade_runbook,
            AUTO_SYNC_MASCARADE_RUNBOOK,
            "## Etat auto-synchronise",
            _render_mascarade_runbook_sync(summary, active_next),
        )
        self._write_report_summary(state)

    def _write_report_summary(self, state: RunState) -> None:
        report_dir = Path(state.report_dir)
        report_dir.mkdir(parents=True, exist_ok=True)
        run_path = report_dir / "run.json"
        summary_path = report_dir / "SUMMARY.md"
        run_path.write_text(json.dumps(asdict(state), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        summary_path.write_text(_render_summary_markdown(state, state.typed_results()), encoding="utf-8")


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _optional_string(value: object) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _slugify(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value).strip("_").lower()


def _command_log(result: CommandResult) -> str:
    return (
        f"$ {' '.join(result.args)}\n"
        f"returncode={result.returncode}\n"
        f"duration_seconds={result.duration_seconds:.2f}\n\n"
        f"STDOUT\n{result.stdout}\n\nSTDERR\n{result.stderr}"
    )


def _build_summary(state: RunState, results: list[ModelRunResult]) -> dict[str, Any]:
    accepted = [item for item in results if item.classification == "accepted"]
    reached_gate = [item for item in results if item.reached_gate()]
    quality_blocked = [item for item in results if item.classification == "quality_blocked"]
    provider_failed = [item for item in results if item.classification == "provider_failed"]
    return {
        "started_at": state.started_at,
        "updated_at": state.updated_at,
        "pending_manual_action": state.pending_manual_action,
        "accepted_models": [item.model for item in accepted],
        "reached_gate_models": [item.model for item in reached_gate],
        "quality_blocked_models": [item.model for item in quality_blocked],
        "provider_failed_models": [item.model for item in provider_failed],
        "results": results,
    }


def _compute_next_lot_recommendation(results: list[ModelRunResult], fallback: str) -> str:
    if any(item.classification == "accepted" for item in results):
        return "Rejouer uniquement les baselines vitesse puis figer la référence locale dans les README/runbooks."
    if any(item.reached_gate() for item in results):
        return "Analyser les runs ayant atteint gate/repair puis resserrer la reference locale autour des meilleurs candidats."
    return fallback


def _render_todo_active_sync(summary: dict[str, Any], next_lot: str) -> str:
    lines = [
        f"- dernier cycle automatique: {summary['updated_at']}",
        f"- modeles accepted: {_comma_or_none(summary['accepted_models'])}",
        f"- modeles ayant atteint gate: {_comma_or_none(summary['reached_gate_models'])}",
        f"- quality_blocked: {_comma_or_none(summary['quality_blocked_models'])}",
        f"- provider_failed: {_comma_or_none(summary['provider_failed_models'])}",
        f"- prochain lot recommande: {next_lot}",
    ]
    if summary["pending_manual_action"]:
        pending = summary["pending_manual_action"]
        lines.extend(
            [
                f"- checkpoint manuel en attente: {pending['reason']}",
                f"- commande preparee: `{pending['command']}`",
                f"- reprise: `python3 scripts/run_next_lots.py --resume {pending['resume_state']}`",
            ]
        )
    return "\n".join(lines)


def _render_todo_done_sync(summary: dict[str, Any]) -> str:
    lines = [
        "- orchestrateur `scripts/run_next_lots.py` disponible",
        "- manifeste `automation/next_lots.toml` charge",
        "- derniers fichiers de suivi synchronisables via marqueurs `AUTO-SYNC`",
        f"- dernier cycle automatise observe: {summary['updated_at']}",
    ]
    return "\n".join(lines)


def _render_plan_sync(summary: dict[str, Any], next_lot: str) -> str:
    lines = [
        f"- dernier verdict automatise: {summary['updated_at']}",
        f"- accepted: {_comma_or_none(summary['accepted_models'])}",
        f"- gate atteint: {_comma_or_none(summary['reached_gate_models'])}",
        f"- prochain lot calcule: {next_lot}",
    ]
    if summary["pending_manual_action"]:
        lines.append(f"- checkpoint manuel requis: {summary['pending_manual_action']['reason']}")
    return "\n".join(lines)


def _render_readme_sync(summary: dict[str, Any], next_lot: str) -> str:
    lines = [
        f"- dernier cycle automatise: {summary['updated_at']}",
        f"- reference locale actuelle: {_reference_label(summary)}",
        f"- prochain lot utile: {next_lot}",
        "- lancer un cycle: `python3 scripts/run_next_lots.py --lot full`",
    ]
    if summary["pending_manual_action"]:
        lines.append(f"- checkpoint manuel en attente: {summary['pending_manual_action']['reason']}")
    return "\n".join(lines)


def _render_runbook_sync(summary: dict[str, Any], project_state: dict[str, Any], next_lot: str) -> str:
    lines = [
        f"- dernier cycle automatise: {summary['updated_at']}",
        f"- chapitre courant detecte: {project_state.get('current_chapter') or 'aucun'}",
        f"- reference locale actuelle: {_reference_label(summary)}",
        f"- prochain lot utile: {next_lot}",
    ]
    if summary["pending_manual_action"]:
        lines.append(f"- reprise attendue apres action manuelle: {summary['pending_manual_action']['resume_state']}")
    return "\n".join(lines)


def _render_mascarade_todo_sync(summary: dict[str, Any], next_lot: str) -> str:
    lines = [
        f"- dernier cycle ANE automatise: {summary['updated_at']}",
        f"- accepted via runtime local: {_comma_or_none(summary['accepted_models'])}",
        f"- gate atteint via runtime local: {_comma_or_none(summary['reached_gate_models'])}",
        f"- blocage runtime principal: {next_lot}",
    ]
    if summary["pending_manual_action"]:
        lines.append(f"- checkpoint runtime manuel: {summary['pending_manual_action']['reason']}")
    return "\n".join(lines)


def _render_mascarade_plan_sync(summary: dict[str, Any], next_lot: str) -> str:
    lines = [
        f"- dernier cycle ANE automatise: {summary['updated_at']}",
        f"- reference locale ANE: {_reference_label(summary)}",
        f"- prochain lot ANE a servir: {next_lot}",
    ]
    return "\n".join(lines)


def _render_mascarade_readme_sync(summary: dict[str, Any], next_lot: str) -> str:
    return "\n".join(
        [
            f"- dernier cycle ANE automatise: {summary['updated_at']}",
            f"- etat de reference ANE: {_reference_label(summary)}",
            f"- prochain lot utile cote pipeline: {next_lot}",
        ]
    )


def _render_mascarade_runbook_sync(summary: dict[str, Any], next_lot: str) -> str:
    lines = [
        f"- dernier cycle ANE automatise: {summary['updated_at']}",
        f"- meilleurs candidats actuels: {_top_candidates(summary['results'])}",
        f"- prochain lot utile cote ANE: {next_lot}",
    ]
    if summary["pending_manual_action"]:
        lines.append(f"- checkpoint runtime manuel: {summary['pending_manual_action']['reason']}")
    return "\n".join(lines)


def _reference_label(summary: dict[str, Any]) -> str:
    if summary["accepted_models"]:
        return summary["accepted_models"][0]
    if summary["reached_gate_models"]:
        return f"aucun accepted, meilleur diagnostic: {summary['reached_gate_models'][0]}"
    return "aucune reference accepted"


def _top_candidates(results: Iterable[ModelRunResult]) -> str:
    candidates = []
    for item in results:
        if item.model in candidates:
            continue
        if item.model.startswith("apple-coreml:qwen3.5-4b") or item.model.startswith("ollama:qwen2.5:7b"):
            candidates.append(item.model)
    return ", ".join(candidates) if candidates else "aucun"


def _comma_or_none(items: list[str]) -> str:
    return ", ".join(items) if items else "aucun"


def _render_comparison_markdown(state: RunState, results: list[ModelRunResult]) -> str:
    lines = [
        f"- dernier cycle automatise: {state.updated_at}",
        "",
        "| Modele | Categorie | Preflight | Smoke | Classification | Failed stage | Gate | Repairs | Notes |",
        "|---|---|---|---|---|---|---|---:|---|",
    ]
    for item in results:
        lines.append(
            "| {model} | {category} | {preflight} | {smoke} | {classification} | {failed_stage} | {gate} | {repairs} | {notes} |".format(
                model=item.model,
                category=item.category,
                preflight="OK" if item.preflight_ok else ("KO" if item.preflight_ok is False else "n/a"),
                smoke="oui" if item.smoke_attempted else "non",
                classification=item.classification,
                failed_stage=item.failed_stage or "",
                gate="oui" if item.reached_gate() else "non",
                repairs=item.repair_attempts,
                notes="; ".join(item.notes) if item.notes else "",
            )
        )
    return "\n".join(lines)


def _render_summary_markdown(state: RunState, results: list[ModelRunResult]) -> str:
    summary = _build_summary(state, results)
    lines = [
        "# Résumé du cycle automatique",
        "",
        f"- lot: `{state.lot}`",
        f"- démarré: `{state.started_at}`",
        f"- mis à jour: `{state.updated_at}`",
        f"- accepted: {_comma_or_none(summary['accepted_models'])}",
        f"- gate atteint: {_comma_or_none(summary['reached_gate_models'])}",
        f"- quality_blocked: {_comma_or_none(summary['quality_blocked_models'])}",
        f"- provider_failed: {_comma_or_none(summary['provider_failed_models'])}",
    ]
    if state.pending_manual_action:
        lines.extend(
            [
                "",
                "## Checkpoint manuel",
                f"- raison: {state.pending_manual_action['reason']}",
                f"- commande: `{state.pending_manual_action['command']}`",
                f"- reprise: `python3 scripts/run_next_lots.py --resume {state.pending_manual_action['resume_state']}`",
            ]
        )
    if results:
        lines.extend(["", "## Résultats", ""])
        lines.append(_render_comparison_markdown(state, results))
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 scripts/run_next_lots.py")
    parser.add_argument("--manifest", default="automation/next_lots.toml")
    parser.add_argument("--lot", default="full", choices=["full", "ensure_models", "runtime_preflight", "priority_models", "baselines", "tracking_sync"])
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
