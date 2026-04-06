#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.reporting import (
    classification_count,
    collect_log_error_counts,
    folder_timestamp,
    iter_run_payloads,
    safe_stamp,
)


def cmd_summary(reports_root: Path) -> int:
    payloads = iter_run_payloads(reports_root)
    if not payloads:
        print("Aucun report trouve.")
        return 0

    latest_by_model: dict[str, tuple[datetime, dict[str, Any]]] = {}
    total_counts: Counter[str] = Counter()

    for _, run in payloads:
        updated = safe_stamp(str(run.get("updated_at", "")))
        for raw in run.get("results") or []:
            if not isinstance(raw, dict):
                continue
            total_counts[str(raw.get("classification", "pending"))] += 1
            model = str(raw.get("model", "")).strip()
            if not model:
                continue
            current = latest_by_model.get(model)
            if current is None or updated >= current[0]:
                latest_by_model[model] = (updated, raw)

    print(f"reports: {len(payloads)}")
    print(
        "global counts: "
        + ", ".join(
            [
                f"accepted={total_counts.get('accepted', 0)}",
                f"quality_blocked={total_counts.get('quality_blocked', 0)}",
                f"provider_failed={total_counts.get('provider_failed', 0)}",
                f"preflight_only={total_counts.get('preflight_only', 0)}",
            ]
        )
    )
    print("")
    print("latest by model:")
    for model in sorted(latest_by_model):
        _, row = latest_by_model[model]
        cls = str(row.get("classification", "pending"))
        status = str(row.get("status", ""))
        failed_stage = str(row.get("failed_stage", ""))
        print(f"- {model}: {cls}, status={status}, failed_stage={failed_stage}")
    return 0


def cmd_analyze_logs(reports_root: Path, top: int) -> int:
    if not reports_root.exists():
        print("Aucun report root trouve.")
        return 0

    error_counts, model_errors = collect_log_error_counts(reports_root)

    print("top erreurs stderr:")
    for msg, count in error_counts.most_common(max(top, 1)):
        print(f"- {count}x {msg}")

    print("")
    print("erreurs par pseudo-modele:")
    for model in sorted(model_errors):
        head = model_errors[model].most_common(1)
        if not head:
            continue
        msg, count = head[0]
        print(f"- {model}: {count}x {msg}")
    return 0


def _folder_timestamp(report_dir: Path) -> datetime:
    return folder_timestamp(report_dir)


def cmd_prune(reports_root: Path, days: int, delete_workspaces: bool, apply: bool) -> int:
    if not reports_root.exists():
        print("Aucun report root trouve.")
        return 0

    keep_after = datetime.now(timezone.utc) - timedelta(days=max(days, 0))
    report_dirs = [p for p in sorted(reports_root.iterdir()) if p.is_dir()]

    deleted = 0
    reclaimed = 0

    for report_dir in report_dirs:
        stamp = _folder_timestamp(report_dir)
        if stamp >= keep_after:
            continue

        if delete_workspaces:
            target = report_dir / "workspaces"
            if target.exists():
                size = sum(f.stat().st_size for f in target.glob("**/*") if f.is_file())
                if apply:
                    shutil.rmtree(target, ignore_errors=True)
                reclaimed += size
                if not apply:
                    print(f"[dry-run] remove workspace {target}")
                else:
                    print(f"removed workspace {target}")
            continue

        size = sum(f.stat().st_size for f in report_dir.glob("**/*") if f.is_file())
        if apply:
            shutil.rmtree(report_dir, ignore_errors=True)
            print(f"removed report {report_dir}")
        else:
            print(f"[dry-run] remove report {report_dir}")
        reclaimed += size
        deleted += 1

    print("")
    print(f"deleted_report_dirs={deleted}")
    print(f"reclaimed_bytes={reclaimed}")
    if not apply:
        print("Aucune suppression effective (mode dry-run). Utiliser --apply pour supprimer.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 scripts/reports_ops.py")
    parser.add_argument("--reports-root", default="automation/reports")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("summary")

    analyze = sub.add_parser("analyze-logs")
    analyze.add_argument("--top", type=int, default=10)

    prune = sub.add_parser("prune")
    prune.add_argument("--days", type=int, default=14)
    prune.add_argument("--delete-workspaces", action="store_true")
    prune.add_argument("--apply", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    reports_root = Path(args.reports_root)

    if args.command == "summary":
        return cmd_summary(reports_root)
    if args.command == "analyze-logs":
        return cmd_analyze_logs(reports_root, top=args.top)
    if args.command == "prune":
        return cmd_prune(
            reports_root,
            days=args.days,
            delete_workspaces=bool(args.delete_workspaces),
            apply=bool(args.apply),
        )

    raise RuntimeError(f"Commande inconnue: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
