from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Iterable


LOG_SUFFIXES = (
    "_ollama_native_preflight.log",
    "_preflight.log",
    "_smoke.log",
)


def safe_read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def safe_stamp(value: str | None) -> datetime:
    if not value:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def iter_run_payloads(reports_root: Path) -> list[tuple[Path, dict[str, Any]]]:
    items: list[tuple[Path, dict[str, Any]]] = []
    for run_path in sorted(reports_root.glob("*/run.json")):
        payload = safe_read_json(run_path)
        if isinstance(payload, dict):
            items.append((run_path, payload))
    return items


def latest_report_run(reports_root: Path) -> dict[str, Any] | None:
    latest: tuple[datetime, dict[str, Any]] | None = None
    for _, payload in iter_run_payloads(reports_root):
        stamp = safe_stamp(str(payload.get("updated_at", "")))
        if latest is None or stamp >= latest[0]:
            latest = (stamp, payload)
    return latest[1] if latest else None


def recent_report_runs(reports_root: Path, limit: int = 5) -> list[tuple[Path, dict[str, Any]]]:
    ranked = sorted(
        iter_run_payloads(reports_root),
        key=lambda item: safe_stamp(str(item[1].get("updated_at", ""))),
        reverse=True,
    )
    return ranked[: max(limit, 0)]


def classification_count(results: Iterable[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for item in results:
        counts[str(item.get("classification", "pending"))] += 1
    return counts


def folder_timestamp(report_dir: Path) -> datetime:
    try:
        return datetime.strptime(report_dir.name, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.fromtimestamp(0, tz=timezone.utc)


def extract_stderr(text: str) -> str:
    marker = "\n\nSTDERR\n"
    if marker not in text:
        return ""
    return text.split(marker, 1)[1].strip()


def build_log_model_lookup(reports_root: Path) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for _, payload in iter_run_payloads(reports_root):
        for raw in payload.get("results") or []:
            if not isinstance(raw, dict):
                continue
            model = str(raw.get("model", "")).strip()
            if not model:
                continue
            for key in ("preflight_log", "smoke_log"):
                value = raw.get(key)
                if not isinstance(value, str) or not value.strip():
                    continue
                lookup[Path(value).name] = model
    return lookup


def log_label_from_path(log_path: Path, *, model_lookup: dict[str, str] | None = None) -> str:
    base = log_path.name
    if model_lookup and base in model_lookup:
        return model_lookup[base]
    if base.startswith("manual_action_"):
        return "manual_action"
    for suffix in LOG_SUFFIXES:
        if base.endswith(suffix):
            return base[: -len(suffix)]
    return log_path.stem


def collect_log_error_counts(reports_root: Path) -> tuple[Counter[str], dict[str, Counter[str]]]:
    error_counts: Counter[str] = Counter()
    model_errors: defaultdict[str, Counter[str]] = defaultdict(Counter)
    model_lookup = build_log_model_lookup(reports_root)

    for log_path in sorted(reports_root.glob("**/*.log")):
        try:
            raw = log_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        stderr = extract_stderr(raw)
        if not stderr:
            continue

        first = ""
        for line in stderr.splitlines():
            clean = line.strip()
            if clean:
                first = clean
                break
        if not first:
            continue

        normalized = re.sub(r"\d+", "<n>", first)
        error_counts[normalized] += 1
        model = log_label_from_path(log_path, model_lookup=model_lookup)
        model_errors[model][normalized] += 1

    return error_counts, dict(model_errors)
