from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from core.reporting import (
    classification_count,
    collect_log_error_counts,
    extract_stderr,
    folder_timestamp,
    latest_report_run,
    log_label_from_path,
    recent_report_runs,
    safe_read_json,
    safe_stamp,
)


class ReportingHelpersTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.reports_root = self.root / "automation" / "reports"
        self.reports_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_run(self, name: str, *, updated_at: str, results: list[dict[str, object]]) -> None:
        report_dir = self.reports_root / name
        report_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "lot": "priority_models",
            "updated_at": updated_at,
            "results": results,
        }
        (report_dir / "run.json").write_text(json.dumps(payload), encoding="utf-8")

    def test_recent_report_runs_sort_by_updated_at_desc(self) -> None:
        self._write_run("20260309T000000Z", updated_at="2026-03-09T00:00:00+00:00", results=[])
        self._write_run("20260310T000000Z", updated_at="2026-03-10T00:00:00+00:00", results=[])
        self._write_run("20260311T000000Z", updated_at="2026-03-11T00:00:00+00:00", results=[])

        recent = recent_report_runs(self.reports_root, limit=2)

        self.assertEqual([path.parent.name for path, _payload in recent], ["20260311T000000Z", "20260310T000000Z"])

    def test_collect_log_error_counts_uses_model_names_from_run_payload(self) -> None:
        report_dir = self.reports_root / "20260314T085946Z"
        report_dir.mkdir(parents=True, exist_ok=True)
        log_path = report_dir / "ollama_qwen2_5_7b_ollama_native_preflight.log"
        log_path.write_text(
            "COMMAND\nollama ...\n\nSTDERR\nHTTP 500 Internal Server Error\n",
            encoding="utf-8",
        )
        self._write_run(
            "20260314T085946Z",
            updated_at="2026-03-14T08:59:46+00:00",
            results=[
                {
                    "model": "ollama:qwen2.5:7b",
                    "preflight_log": str(log_path),
                }
            ],
        )

        error_counts, model_errors = collect_log_error_counts(self.reports_root)

        self.assertEqual(error_counts["HTTP <n> Internal Server Error"], 1)
        self.assertIn("ollama:qwen2.5:7b", model_errors)
        self.assertEqual(model_errors["ollama:qwen2.5:7b"]["HTTP <n> Internal Server Error"], 1)

    def test_log_label_from_path_keeps_manual_action_readable(self) -> None:
        label = log_label_from_path(Path("/tmp/manual_action_00.log"))
        self.assertEqual(label, "manual_action")

    def test_log_label_strips_smoke_suffix(self) -> None:
        label = log_label_from_path(Path("/tmp/ollama_qwen2_5_7b_smoke.log"))
        self.assertEqual(label, "ollama_qwen2_5_7b")

    def test_log_label_strips_preflight_suffix(self) -> None:
        label = log_label_from_path(Path("/tmp/ollama_qwen2_5_1_5b_preflight.log"))
        self.assertEqual(label, "ollama_qwen2_5_1_5b")

    def test_log_label_uses_model_lookup_when_available(self) -> None:
        lookup = {"model_smoke.log": "ollama:qwen2.5:7b"}
        label = log_label_from_path(Path("/tmp/model_smoke.log"), model_lookup=lookup)
        self.assertEqual(label, "ollama:qwen2.5:7b")

    def test_log_label_falls_back_to_stem(self) -> None:
        label = log_label_from_path(Path("/tmp/unknown_log_file.log"))
        self.assertEqual(label, "unknown_log_file")

    def test_safe_read_json_returns_dict(self) -> None:
        path = self.root / "test.json"
        path.write_text('{"key": "value"}', encoding="utf-8")
        result = safe_read_json(path)
        self.assertEqual(result, {"key": "value"})

    def test_safe_read_json_returns_none_on_missing_file(self) -> None:
        result = safe_read_json(self.root / "nonexistent.json")
        self.assertIsNone(result)

    def test_safe_read_json_returns_none_on_invalid_json(self) -> None:
        path = self.root / "bad.json"
        path.write_text("not json", encoding="utf-8")
        result = safe_read_json(path)
        self.assertIsNone(result)

    def test_safe_stamp_parses_iso_with_tz(self) -> None:
        from datetime import timezone
        stamp = safe_stamp("2026-03-16T12:00:00+00:00")
        self.assertEqual(stamp.tzinfo, timezone.utc)
        self.assertEqual(stamp.year, 2026)

    def test_safe_stamp_returns_epoch_on_empty(self) -> None:
        stamp = safe_stamp("")
        self.assertEqual(stamp.year, 1970)

    def test_safe_stamp_returns_epoch_on_invalid(self) -> None:
        stamp = safe_stamp("not-a-date")
        self.assertEqual(stamp.year, 1970)

    def test_extract_stderr_returns_empty_when_no_marker(self) -> None:
        result = extract_stderr("just some output\nmore lines")
        self.assertEqual(result, "")

    def test_extract_stderr_returns_content_after_marker(self) -> None:
        text = "stdout stuff\n\nSTDERR\nError: timeout\nmore error"
        result = extract_stderr(text)
        self.assertEqual(result, "Error: timeout\nmore error")

    def test_classification_count_counts_correctly(self) -> None:
        results = [
            {"classification": "accepted"},
            {"classification": "quality_blocked"},
            {"classification": "quality_blocked"},
            {"classification": "provider_failed"},
        ]
        counts = classification_count(results)
        self.assertEqual(counts["accepted"], 1)
        self.assertEqual(counts["quality_blocked"], 2)
        self.assertEqual(counts["provider_failed"], 1)

    def test_classification_count_defaults_to_pending(self) -> None:
        results = [{"status": "running"}]
        counts = classification_count(results)
        self.assertEqual(counts["pending"], 1)

    def test_folder_timestamp_parses_valid_name(self) -> None:
        from datetime import timezone
        ts = folder_timestamp(Path("automation/reports/20260316T193455Z"))
        self.assertEqual(ts.year, 2026)
        self.assertEqual(ts.month, 3)
        self.assertEqual(ts.day, 16)
        self.assertEqual(ts.tzinfo, timezone.utc)

    def test_folder_timestamp_returns_epoch_on_invalid_name(self) -> None:
        ts = folder_timestamp(Path("automation/reports/invalid-name"))
        self.assertEqual(ts.year, 1970)

    def test_latest_report_run_returns_most_recent(self) -> None:
        self._write_run("20260309T000000Z", updated_at="2026-03-09T00:00:00+00:00", results=[])
        self._write_run("20260316T000000Z", updated_at="2026-03-16T00:00:00+00:00", results=[])
        result = latest_report_run(self.reports_root)
        self.assertIsNotNone(result)
        self.assertEqual(result["updated_at"], "2026-03-16T00:00:00+00:00")

    def test_latest_report_run_returns_none_on_empty_dir(self) -> None:
        result = latest_report_run(self.reports_root)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
