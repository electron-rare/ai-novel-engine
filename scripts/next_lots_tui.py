#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
import time

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.reporting import classification_count, latest_report_run, safe_read_json


def _short(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    if width <= 3:
        return text[:width]
    return text[: width - 3] + "..."


def _render(state: dict[str, object] | None, latest_run: dict[str, object] | None, reports_root: Path) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    lines: list[str] = []
    lines.append("AI Novel Engine - Next Lots TUI")
    lines.append(f"UTC now: {now}")
    lines.append(f"reports root: {reports_root}")
    lines.append("")

    if not state:
        lines.append("state: absent ou illisible")
    else:
        step_index = int(state.get("step_index", 0))
        model_index = int(state.get("model_index", 0))
        steps = state.get("steps") or []
        lot = str(state.get("lot", ""))
        updated = str(state.get("updated_at", ""))
        pending = state.get("pending_manual_action")
        results = state.get("results") or []
        counts = classification_count([item for item in results if isinstance(item, dict)])

        lines.append(f"lot: {lot}")
        lines.append(f"updated_at: {updated}")
        lines.append(f"progress: step {step_index + 1}/{max(len(steps), 1)}  model_index={model_index}")
        lines.append(
            "results: "
            + ", ".join(
                [
                    f"accepted={counts.get('accepted', 0)}",
                    f"quality_blocked={counts.get('quality_blocked', 0)}",
                    f"provider_failed={counts.get('provider_failed', 0)}",
                    f"preflight_only={counts.get('preflight_only', 0)}",
                    f"pending={counts.get('pending', 0)}",
                ]
            )
        )

        if pending:
            reason = str(pending.get("reason", ""))
            resume = str(pending.get("resume_state", ""))
            lines.append("checkpoint: OUI")
            lines.append(f"reason: {_short(reason, 120)}")
            lines.append(f"resume: {_short(resume, 120)}")
        else:
            lines.append("checkpoint: non")

        lines.append("")
        lines.append("dernieres classifications:")
        recent = [item for item in results if isinstance(item, dict)][-8:]
        if not recent:
            lines.append("- aucune")
        for item in recent:
            model = str(item.get("model", ""))
            cls = str(item.get("classification", "pending"))
            status = str(item.get("status", ""))
            lines.append(f"- {model} -> {cls} ({status})")

    lines.append("")
    lines.append("latest report snapshot:")
    if not latest_run:
        lines.append("- aucun run.json historise")
    else:
        lines.append(f"- lot: {latest_run.get('lot', '')}")
        lines.append(f"- updated_at: {latest_run.get('updated_at', '')}")
        results = latest_run.get("results") or []
        counts = classification_count([item for item in results if isinstance(item, dict)])
        lines.append(
            "- counts: "
            + ", ".join(
                [
                    f"accepted={counts.get('accepted', 0)}",
                    f"quality_blocked={counts.get('quality_blocked', 0)}",
                    f"provider_failed={counts.get('provider_failed', 0)}",
                ]
            )
        )

    lines.append("")
    lines.append("tips:")
    lines.append("- resume: python3 scripts/run_next_lots.py --resume automation/state/next_lots_state.json")
    lines.append("- sync docs only: python3 scripts/run_next_lots.py --lot tracking_sync --report-only")
    return "\n".join(lines)


def _draw_once(state_path: Path, reports_root: Path) -> str:
    state = safe_read_json(state_path)
    latest = latest_report_run(reports_root)
    return _render(state, latest, reports_root)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 scripts/next_lots_tui.py")
    parser.add_argument("--state", default="automation/state/next_lots_state.json")
    parser.add_argument("--reports-root", default="automation/reports")
    parser.add_argument("--watch", action="store_true", help="Rafraichit en boucle la vue TUI.")
    parser.add_argument("--interval", type=float, default=2.0, help="Intervalle de rafraichissement en secondes.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    state_path = Path(args.state)
    reports_root = Path(args.reports_root)

    if args.watch:
        interval = max(0.2, float(args.interval))
        try:
            while True:
                print("\033[2J\033[H", end="")
                print(_draw_once(state_path, reports_root))
                time.sleep(interval)
        except KeyboardInterrupt:
            return 0
    else:
        print(_draw_once(state_path, reports_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
