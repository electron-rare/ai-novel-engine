#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
import time
import tomllib
from typing import Any
from urllib import request as urllib_request, error as urllib_error

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.project.loader import ProjectState
from core.reporting import (
    classification_count,
    collect_log_error_counts,
    recent_report_runs,
    safe_read_json,
)
from core.runtime.config import runtime_probe_profile
from core.runtime.health import probe_runtime_health
from core.runtime.profiles import runtime_probe_name


def _short(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    if width <= 3:
        return text[:width]
    return text[: width - 3] + "..."


def _human_bytes(value: int) -> str:
    size = float(max(value, 0))
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}GB"


def _safe_manifest(path: Path) -> dict[str, Any]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}



def _probe_url(url: str, timeout: float = 1.5) -> bool:
    """Retourne True si l'URL répond avec un code HTTP, quelle que soit la valeur."""
    try:
        urllib_request.urlopen(url, timeout=timeout)
        return True
    except urllib_error.HTTPError:
        return True  # le serveur répond (ex: 404 Ollama /health)
    except (OSError, ValueError, urllib_error.URLError):
        return False


def _probe_openai_runtime(base_url: str, timeout: float = 1.5, *, probe_kind: str = "core") -> tuple[bool, str | None]:
    profile = runtime_probe_profile(base_url, timeout=timeout, name=runtime_probe_name(probe_kind))
    health = probe_runtime_health(profile)
    return health.ok, health.active_model


def _reports_size_bytes(reports_root: Path) -> int:
    return sum(path.stat().st_size for path in reports_root.glob("**/*") if path.is_file())


def _render_project(project: ProjectState) -> list[str]:
    state = project.summary()
    lines = [
        "projet:",
        f"- chapitre courant: {state['current_chapter'] or 'aucun'}",
        f"- chapitres connus: {len(state['known_chapters'])}",
        f"- en attente de validation: {len(state['awaiting_acceptance'])}",
        f"- quality_blocked: {len(state['quality_blocked_chapters'])}",
        f"- failed: {len(state['failed_chapters'])}",
    ]

    if state["awaiting_acceptance"]:
        lines.append("- attente la plus recente: " + str(state["awaiting_acceptance"][0]["chapter"]))
    if state["quality_blocked_chapters"]:
        blocked = state["quality_blocked_chapters"][0]
        blockers = ", ".join(blocked["quality_blockers"]) if blocked["quality_blockers"] else "inconnu"
        lines.append(f"- premier blocage qualite: {blocked['chapter']} ({blockers})")
    if state["failed_chapters"]:
        failed = state["failed_chapters"][0]
        lines.append(f"- premier echec runtime: {failed['chapter']} ({failed['failed_stage'] or 'n/a'})")
    return lines


def _render_automation(state: dict[str, Any] | None) -> list[str]:
    lines = ["automation:"]
    if not state:
        lines.append("- etat: absent ou illisible")
        return lines

    step_index = int(state.get("step_index", 0))
    steps = state.get("steps") or []
    results = [item for item in (state.get("results") or []) if isinstance(item, dict)]
    counts = classification_count(results)
    lines.extend(
        [
            f"- lot: {state.get('lot', '')}",
            f"- updated_at: {state.get('updated_at', '')}",
            f"- progression: step {step_index + 1}/{max(len(steps), 1)}",
            (
                "- resultats: "
                + ", ".join(
                    [
                        f"accepted={counts.get('accepted', 0)}",
                        f"quality_blocked={counts.get('quality_blocked', 0)}",
                        f"provider_failed={counts.get('provider_failed', 0)}",
                        f"preflight_only={counts.get('preflight_only', 0)}",
                    ]
                )
            ),
        ]
    )

    pending = state.get("pending_manual_action")
    if isinstance(pending, dict):
        lines.append("- checkpoint: OUI")
        lines.append(f"- raison: {_short(str(pending.get('reason', '')), 110)}")
        lines.append(f"- reprise: {_short(str(pending.get('resume_state', '')), 110)}")
    else:
        lines.append("- checkpoint: non")

    recommendation = str(state.get("next_recommended_lot", "")).strip()
    if recommendation:
        lines.append(f"- suite: {_short(recommendation, 110)}")
    return lines


def _render_manifest(manifest: dict[str, Any]) -> list[str]:
    paths = manifest.get("paths") if isinstance(manifest, dict) else {}
    if not isinstance(paths, dict):
        paths = {}

    def _tag(url: str, probe_url: str | None = None) -> str:
        target = probe_url or url
        if not target or target == "n/a":
            return "n/a"
        up = _probe_url(target)
        return f"{url}  [{'UP' if up else 'DOWN'}]"

    def _runtime_tag(url: str) -> str:
        if not url or url == "n/a":
            return "n/a"
        probe_kind = "core"
        if url == apple_url:
            probe_kind = "apple"
        elif url == ollama_openai_url:
            probe_kind = "ollama_openai"
        up, active_model = _probe_openai_runtime(url, probe_kind=probe_kind)
        suffix = f" model={active_model}" if active_model else ""
        return f"{url}  [{'UP' if up else 'DOWN'}{suffix}]"

    core_url = str(paths.get("core_base_url", "n/a"))
    apple_url = str(paths.get("apple_runtime_url", "n/a"))
    ollama_tags_url = str(paths.get("ollama_tags_url", "n/a"))
    ollama_runtime = str(paths.get("ollama_runtime", "n/a"))
    ollama_openai_url = str(paths.get("ollama_openai_base_url", "n/a"))

    # Ollama daemon répond sur /api/tags, pas /health
    ollama_health_url = ollama_tags_url if "api/tags" in ollama_tags_url else ollama_tags_url

    return [
        "runtime:",
        f"- core:          {_runtime_tag(core_url)}",
        f"- apple:         {_runtime_tag(apple_url)}",
        f"- ollama daemon: {_tag(ollama_tags_url, ollama_health_url)}",
        f"- ollama runtime: {ollama_runtime}",
        f"- ollama openai: {_runtime_tag(ollama_openai_url)}",
    ]


def _render_recent_reports(reports_root: Path, limit: int) -> list[str]:
    lines = ["reports recents:"]
    recent = recent_report_runs(reports_root, limit=limit)
    if not recent:
        lines.append("- aucun run.json historise")
        return lines

    for run_path, payload in recent:
        results = [item for item in payload.get("results") or [] if isinstance(item, dict)]
        counts = classification_count(results)
        lines.append(
            "- {name} | lot={lot} | accepted={accepted} qb={qb} pf={pf}".format(
                name=run_path.parent.name,
                lot=payload.get("lot", ""),
                accepted=counts.get("accepted", 0),
                qb=counts.get("quality_blocked", 0),
                pf=counts.get("provider_failed", 0),
            )
        )
    return lines


def _render_log_section(reports_root: Path, top: int) -> list[str]:
    lines = ["logs:"]
    error_counts, model_errors = collect_log_error_counts(reports_root)
    if not error_counts:
        lines.append("- aucune erreur stderr agregee")
        return lines

    lines.append("- top erreurs:")
    for message, count in error_counts.most_common(max(top, 1)):
        lines.append(f"  {count}x {message}")

    lines.append("- principaux modeles:")
    shown = 0
    for model in sorted(model_errors):
        head = model_errors[model].most_common(1)
        if not head:
            continue
        message, count = head[0]
        lines.append(f"  {model}: {count}x {message}")
        shown += 1
        if shown >= top:
            break
    return lines


def _render_footer(reports_root: Path) -> list[str]:
    size_bytes = _reports_size_bytes(reports_root)
    return [
        "actions utiles:",
        "- python3 scripts/next_lots_tui.py --watch --interval 2",
        "- python3 scripts/reports_ops.py summary",
        "- python3 scripts/reports_ops.py analyze-logs --top 10",
        "- python3 scripts/reports_ops.py prune --days 14",
        f"- empreinte reports: {_human_bytes(size_bytes)}",
    ]


def _render(root: Path, state_path: Path, reports_root: Path, manifest_path: Path, recent: int, top: int) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    project = ProjectState(root)
    state = safe_read_json(state_path)
    manifest = _safe_manifest(manifest_path)

    sections = [
        [
            "AI Novel Engine - Ops TUI",
            f"utc now: {now}",
            f"repo root: {root}",
            f"manifest: {manifest_path}",
            "",
        ],
        _render_manifest(manifest),
        _render_project(project),
        _render_automation(state),
        _render_recent_reports(reports_root, recent),
        _render_log_section(reports_root, top),
        _render_footer(reports_root),
    ]
    return "\n\n".join("\n".join(section) for section in sections)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 scripts/ops_tui.py")
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument("--manifest", default="automation/next_lots.toml")
    parser.add_argument("--state", default="automation/state/next_lots_state.json")
    parser.add_argument("--reports-root", default="automation/reports")
    parser.add_argument("--recent", type=int, default=5, help="Nombre de reports recents affiches.")
    parser.add_argument("--top", type=int, default=5, help="Nombre d'erreurs stderr agregees.")
    parser.add_argument("--watch", action="store_true", help="Rafraichit en boucle la vue TUI.")
    parser.add_argument("--interval", type=float, default=3.0, help="Intervalle de rafraichissement en secondes.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root)
    manifest_path = root / args.manifest if not Path(args.manifest).is_absolute() else Path(args.manifest)
    state_path = root / args.state if not Path(args.state).is_absolute() else Path(args.state)
    reports_root = root / args.reports_root if not Path(args.reports_root).is_absolute() else Path(args.reports_root)

    def draw() -> None:
        print(
            _render(
                root=root,
                state_path=state_path,
                reports_root=reports_root,
                manifest_path=manifest_path,
                recent=max(args.recent, 1),
                top=max(args.top, 1),
            )
        )

    if args.watch:
        interval = max(0.5, float(args.interval))
        try:
            while True:
                print("\033[2J\033[H", end="")
                draw()
                time.sleep(interval)
        except KeyboardInterrupt:
            return 0
    else:
        draw()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
