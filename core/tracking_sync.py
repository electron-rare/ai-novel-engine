from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import re
import tempfile
from pathlib import Path
from typing import Any, Iterable

from core.project.loader import ProjectState
from core.reporting import iter_run_payloads, safe_stamp


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
class TrackingSyncContext:
    repo_root: Path
    next_code_lot: str
    ane_todo_active: Path
    ane_todo_done: Path
    ane_plan: Path
    ane_comparison: Path
    ane_readme: Path
    ane_runbook: Path
    mascarade_todo: Path
    mascarade_plan: Path
    mascarade_readme: Path
    mascarade_runbook: Path


def build_tracking_sync_context(
    repo_root: Path,
    *,
    next_code_lot: str,
    tracking: TrackingPaths,
) -> TrackingSyncContext:
    return TrackingSyncContext(
        repo_root=repo_root,
        next_code_lot=next_code_lot,
        ane_todo_active=tracking.ane_todo_active,
        ane_todo_done=tracking.ane_todo_done,
        ane_plan=tracking.ane_plan,
        ane_comparison=tracking.ane_comparison,
        ane_readme=tracking.ane_readme,
        ane_runbook=tracking.ane_runbook,
        mascarade_todo=tracking.mascarade_todo,
        mascarade_plan=tracking.mascarade_plan,
        mascarade_readme=tracking.mascarade_readme,
        mascarade_runbook=tracking.mascarade_runbook,
    )


@dataclass(frozen=True)
class TrackingResult:
    model: str
    category: str
    classification: str = "pending"
    preflight_ok: bool | None = None
    smoke_attempted: bool = False
    status: str | None = None
    accepted: bool = False
    failed_stage: str | None = None
    quality_blockers: list[str] = field(default_factory=list)
    retry_stages: list[str] = field(default_factory=list)
    repair_attempts: int = 0
    notes: list[str] = field(default_factory=list)
    completed_stages: list[str] = field(default_factory=list)
    repair_models: list[str] = field(default_factory=list)

    def reached_gate(self) -> bool:
        return "gate" in self.completed_stages or self.failed_stage == "gate"


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
    repeated_heading_pattern = rf"(?:{re.escape(heading)}\n){{2,}}"
    new_text = re.sub(repeated_heading_pattern, f"{heading}\n", new_text)
    path.write_text(new_text, encoding="utf-8")


def sync_tracking(context: TrackingSyncContext, state: Any, *, dry_run: bool, project_state: dict[str, Any] | None = None) -> None:
    if dry_run:
        write_report_summary(state)
        return
    typed_results = _consolidated_tracking_results(state, context.repo_root / "automation" / "reports")
    accepted_counts = _accepted_history_counts(state, context.repo_root / "automation" / "reports")
    project_state = project_state or ProjectState(context.repo_root).summary()
    summary = _build_summary(state, typed_results)
    comparison = _render_comparison_markdown(state, typed_results)
    active_next = _compute_next_lot_recommendation(
        typed_results,
        context.next_code_lot,
        accepted_counts=accepted_counts,
    )

    replace_auto_section(
        context.ane_todo_active,
        AUTO_SYNC_TODO_ACTIVE,
        "## Auto-sync",
        _render_todo_active_sync(summary, active_next),
    )
    replace_auto_section(
        context.ane_todo_done,
        AUTO_SYNC_TODO_DONE,
        "## Auto-sync",
        _render_todo_done_sync(summary),
    )
    replace_auto_section(
        context.ane_plan,
        AUTO_SYNC_PLAN,
        "## Auto-sync",
        _render_plan_sync(summary, active_next),
    )
    replace_auto_section(
        context.ane_comparison,
        AUTO_SYNC_COMPARISON,
        "## Auto-sync",
        comparison,
    )
    replace_auto_section(
        context.ane_readme,
        AUTO_SYNC_README,
        "## Etat auto-synchronise",
        _render_readme_sync(summary, active_next),
    )
    replace_auto_section(
        context.ane_runbook,
        AUTO_SYNC_RUNBOOK,
        "## Etat auto-synchronise",
        _render_runbook_sync(summary, project_state, active_next),
    )
    replace_auto_section(
        context.mascarade_todo,
        AUTO_SYNC_MASCARADE_TODO,
        "## Auto-sync",
        _render_mascarade_todo_sync(summary, active_next),
    )
    replace_auto_section(
        context.mascarade_plan,
        AUTO_SYNC_MASCARADE_PLAN,
        "## Auto-sync",
        _render_mascarade_plan_sync(summary, active_next),
    )
    replace_auto_section(
        context.mascarade_readme,
        AUTO_SYNC_MASCARADE_README,
        "## Etat auto-synchronise",
        _render_mascarade_readme_sync(summary, active_next),
    )
    replace_auto_section(
        context.mascarade_runbook,
        AUTO_SYNC_MASCARADE_RUNBOOK,
        "## Etat auto-synchronise",
        _render_mascarade_runbook_sync(summary, active_next),
    )
    write_report_summary(state)


def write_report_summary(state: Any) -> None:
    report_dir = Path(getattr(state, "report_dir"))
    report_dir.mkdir(parents=True, exist_ok=True)
    run_path = report_dir / "run.json"
    summary_path = report_dir / "SUMMARY.md"
    state_payload = dict(vars(state))
    run_path.write_text(json.dumps(state_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    typed_results = list(_state_typed_results(state))
    summary_path.write_text(_render_summary_markdown(state, typed_results), encoding="utf-8")


def _safe_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _load_report_history(reports_root: Path) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    if not reports_root.exists():
        return history
    for run_path, payload in iter_run_payloads(reports_root):
        payload = dict(payload)
        payload.setdefault("report_dir", str(run_path.parent))
        history.append(payload)
    history.sort(key=lambda item: (_safe_timestamp(str(item.get("updated_at", ""))), str(item.get("report_dir", ""))))
    return history


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _optional_string(value: object) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _tracking_result_from_payload(payload: Any) -> TrackingResult | None:
    if isinstance(payload, TrackingResult):
        return payload
    if not isinstance(payload, dict):
        payload = {field: getattr(payload, field, None) for field in (
            "model",
            "category",
            "classification",
            "preflight_ok",
            "smoke_attempted",
            "status",
            "accepted",
            "failed_stage",
            "quality_blockers",
            "retry_stages",
            "repair_attempts",
            "notes",
            "completed_stages",
            "repair_models",
        )}
    model = str(payload.get("model", "")).strip()
    category = str(payload.get("category", "")).strip()
    if not model or not category:
        return None
    return TrackingResult(
        model=model,
        category=category,
        classification=str(payload.get("classification", "pending")),
        preflight_ok=payload.get("preflight_ok"),
        smoke_attempted=bool(payload.get("smoke_attempted", False)),
        status=_optional_string(payload.get("status")),
        accepted=bool(payload.get("accepted", False)),
        failed_stage=_optional_string(payload.get("failed_stage")),
        quality_blockers=_string_list(payload.get("quality_blockers")),
        retry_stages=_string_list(payload.get("retry_stages")),
        repair_attempts=int(payload.get("repair_attempts", 0) or 0),
        notes=_string_list(payload.get("notes")),
        completed_stages=_string_list(payload.get("completed_stages")),
        repair_models=_string_list(payload.get("repair_models")),
    )


def _state_typed_results(state: Any) -> list[TrackingResult]:
    results: list[TrackingResult] = []
    typed_results = getattr(state, "typed_results", None)
    raw_results = typed_results() if callable(typed_results) else getattr(state, "results", [])
    for item in raw_results or []:
        result = _tracking_result_from_payload(item)
        if result is not None:
            results.append(result)
    return results


def _consolidated_tracking_results(state: Any, reports_root: Path) -> list[TrackingResult]:
    latest_by_model: dict[str, tuple[tuple[datetime, int], TrackingResult]] = {}
    sequence = 0
    for snapshot in [*_load_report_history(reports_root), _state_payload(state)]:
        stamp = _safe_timestamp(str(snapshot.get("updated_at", "")))
        for result in _snapshot_results(snapshot):
            candidate_key = (stamp, sequence)
            current = latest_by_model.get(result.model)
            if current is None or candidate_key >= current[0]:
                latest_by_model[result.model] = (candidate_key, result)
            sequence += 1
    return sorted((payload[1] for payload in latest_by_model.values()), key=_result_sort_key)


def _accepted_history_counts(state: Any, reports_root: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for snapshot in [*_load_report_history(reports_root), _state_payload(state)]:
        for result in _snapshot_results(snapshot):
            if result.classification != "accepted":
                continue
            counts[result.model] = counts.get(result.model, 0) + 1
    return counts


def _snapshot_results(snapshot: dict[str, Any]) -> list[TrackingResult]:
    results: list[TrackingResult] = []
    for item in snapshot.get("results") or []:
        result = _tracking_result_from_payload(item)
        if result is not None:
            results.append(result)
    return results


def _state_payload(state: Any) -> dict[str, Any]:
    payload = dict(vars(state))
    if "report_dir" in payload:
        payload["report_dir"] = str(payload["report_dir"])
    return payload


def _result_sort_key(result: TrackingResult) -> tuple[int, str, str]:
    category_order = {
        "priority_models": 0,
        "baselines": 1,
        "preflight_only": 2,
        "runtime_preflight": 3,
    }
    provider = result.model.split(":", 1)[0]
    return (category_order.get(result.category, 9), provider, result.model)


def _build_summary(state: Any, results: list[TrackingResult]) -> dict[str, Any]:
    accepted = [item for item in results if item.classification == "accepted"]
    reached_gate = [item for item in results if item.reached_gate()]
    quality_blocked = [item for item in results if item.classification == "quality_blocked"]
    provider_failed = [item for item in results if item.classification == "provider_failed"]
    return {
        "started_at": getattr(state, "started_at"),
        "updated_at": getattr(state, "updated_at"),
        "pending_manual_action": getattr(state, "pending_manual_action", None),
        "accepted_models": [item.model for item in accepted],
        "reached_gate_models": [item.model for item in reached_gate],
        "quality_blocked_models": [item.model for item in quality_blocked],
        "provider_failed_models": [item.model for item in provider_failed],
        "results": results,
    }


def _compute_next_lot_recommendation(
    results: list[TrackingResult],
    fallback: str,
    *,
    accepted_counts: dict[str, int] | None = None,
) -> str:
    accepted_counts = accepted_counts or {}
    provider_failed_models = [item.model for item in results if item.classification == "provider_failed"]
    has_quality_blocked = any(item.classification == "quality_blocked" for item in results)
    if accepted_counts.get("apple-coreml:qwen3.5-4b-onnx-q4f16", 0) >= 2:
        if provider_failed_models:
            if has_quality_blocked:
                return "Reference locale reconfirmee; retablir le runtime des modeles provider_failed puis reprendre rewrite/repair sur les modeles bloques a gate."
            return "Reference locale reconfirmee; retablir le runtime des modeles provider_failed avant de poursuivre."
        if any(item.classification == "quality_blocked" for item in results):
            return "Reference locale reconfirmee; resserrer rewrite/repair sur les modeles deja bloques a gate."
        return "Reference locale reconfirmee; garder les autres modeles en regression."
    if any(item.classification == "accepted" for item in results):
        if provider_failed_models:
            return "Confirmer la reference accepted puis retablir le runtime des modeles provider_failed."
        if any(item.classification == "quality_blocked" for item in results):
            return "Confirmer la reference accepted puis resserrer rewrite/repair sur les modeles deja bloques a gate."
        return "Figer la reference locale dans les README/runbooks et garder les autres modeles en regression."
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


def _top_candidates(results: Iterable[TrackingResult]) -> str:
    candidates: list[str] = []
    for item in results:
        if item.model in candidates:
            continue
        if item.model.startswith("apple-coreml:qwen3.5-4b") or item.model.startswith("ollama:qwen2.5:7b"):
            candidates.append(item.model)
    return ", ".join(candidates) if candidates else "aucun"


def _comma_or_none(items: list[str]) -> str:
    return ", ".join(items) if items else "aucun"


def _render_comparison_markdown(state: Any, results: list[TrackingResult]) -> str:
    lines = [
        f"- dernier cycle automatise: {getattr(state, 'updated_at')}",
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


def _render_summary_markdown(state: Any, results: list[TrackingResult]) -> str:
    summary = _build_summary(state, results)
    lines = [
        "# Résumé du cycle automatique",
        "",
        f"- lot: `{getattr(state, 'lot')}`",
        f"- démarré: `{getattr(state, 'started_at')}`",
        f"- mis à jour: `{getattr(state, 'updated_at')}`",
        f"- accepted: {_comma_or_none(summary['accepted_models'])}",
        f"- gate atteint: {_comma_or_none(summary['reached_gate_models'])}",
        f"- quality_blocked: {_comma_or_none(summary['quality_blocked_models'])}",
        f"- provider_failed: {_comma_or_none(summary['provider_failed_models'])}",
    ]
    if getattr(state, "pending_manual_action", None):
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
