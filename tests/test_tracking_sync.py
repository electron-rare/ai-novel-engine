from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path
import tempfile
import unittest

from core.tracking_sync import (
    TrackingPaths,
    build_tracking_sync_context,
    sync_tracking,
    write_report_summary,
)


class TrackingSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "repo"
        self.root.mkdir(parents=True, exist_ok=True)
        self.mascarade = Path(self.temp_dir.name) / "mascarade"
        self.mascarade.mkdir(parents=True, exist_ok=True)
        self.report_dir = self.root / "automation" / "reports" / "20260322T120000Z"
        self.report_dir.mkdir(parents=True, exist_ok=True)

        self.tracking = TrackingPaths(
            ane_todo_active=self._write_doc(self.root / "TODO_ACTIVE.md", "## Auto-sync", "ANE-TODO-ACTIVE"),
            ane_todo_done=self._write_doc(self.root / "TODO_IMPLEMENTE.md", "## Auto-sync", "ANE-TODO-DONE"),
            ane_plan=self._write_doc(self.root / "docs" / "EXECUTION_PLAN_2026-03-21.md", "## Auto-sync", "ANE-PLAN"),
            ane_comparison=self._write_doc(self.root / "docs" / "MODEL_COMPARISON_2026-03-21.md", "## Auto-sync", "ANE-COMPARISON"),
            ane_readme=self._write_doc(self.root / "README.md", "## Etat auto-synchronise", "ANE-README"),
            ane_runbook=self._write_doc(self.root / "docs" / "runbooks" / "LOCAL_GENERATION.md", "## Etat auto-synchronise", "ANE-RUNBOOK"),
            mascarade_repo=self.mascarade,
            mascarade_todo=self._write_doc(self.mascarade / "TODO_AI_NOVEL_ENGINE.md", "## Auto-sync", "MASCARADE-TODO"),
            mascarade_plan=self._write_doc(self.mascarade / "docs" / "EXECUTION_PLAN_2026-03-21.md", "## Auto-sync", "MASCARADE-PLAN"),
            mascarade_readme=self._write_doc(self.mascarade / "README.md", "## Etat auto-synchronise", "MASCARADE-README"),
            mascarade_runbook=self._write_doc(self.mascarade / "docs" / "RUNBOOK_APPLE_LLM_LOCAL.md", "## Etat auto-synchronise", "MASCARADE-RUNBOOK"),
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_doc(self, path: Path, heading: str, marker: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(
                [
                    f"# {path.name}",
                    "",
                    heading,
                    f"<!-- AUTO-SYNC:{marker}:START -->",
                    "- old",
                    f"<!-- AUTO-SYNC:{marker}:END -->",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return path

    def _state(self) -> SimpleNamespace:
        return SimpleNamespace(
            lot="priority_models",
            started_at="2026-03-22T12:00:00+00:00",
            updated_at="2026-03-22T12:05:00+00:00",
            report_dir=str(self.report_dir),
            state_path=str(self.root / "automation" / "state" / "next_lots_state.json"),
            pending_manual_action=None,
            results=[
                {
                    "model": "apple-coreml:qwen3.5-4b-onnx-q4f16",
                    "category": "priority_models",
                    "classification": "accepted",
                    "preflight_ok": True,
                    "smoke_attempted": True,
                    "status": "accepted",
                    "accepted": True,
                    "completed_stages": ["gate", "repair"],
                    "repair_attempts": 0,
                    "notes": ["ok"],
                }
            ],
        )

    def test_build_tracking_sync_context_maps_all_paths(self) -> None:
        context = build_tracking_sync_context(
            self.root,
            next_code_lot="rewrite_compaction",
            tracking=self.tracking,
        )

        self.assertEqual(context.repo_root, self.root)
        self.assertEqual(context.next_code_lot, "rewrite_compaction")
        self.assertEqual(context.ane_todo_active, self.tracking.ane_todo_active)
        self.assertEqual(context.mascarade_runbook, self.tracking.mascarade_runbook)

    def test_sync_tracking_updates_docs_and_writes_summary(self) -> None:
        context = build_tracking_sync_context(
            self.root,
            next_code_lot="rewrite_compaction",
            tracking=self.tracking,
        )

        sync_tracking(context, self._state(), dry_run=False, project_state={"current_chapter": "05"})

        todo_active = self.tracking.ane_todo_active.read_text(encoding="utf-8")
        summary = (self.report_dir / "SUMMARY.md").read_text(encoding="utf-8")
        self.assertIn("apple-coreml:qwen3.5-4b-onnx-q4f16", todo_active)
        self.assertIn("prochain lot recommande", todo_active)
        self.assertIn("| Modele | Categorie | Preflight | Smoke | Classification | Failed stage | Gate | Repairs | Notes |", summary)
        self.assertIn("accepted", summary)

    def test_write_report_summary_keeps_report_directory_atomic(self) -> None:
        state = self._state()

        write_report_summary(state)

        run_path = self.report_dir / "run.json"
        summary_path = self.report_dir / "SUMMARY.md"
        self.assertTrue(run_path.exists())
        self.assertTrue(summary_path.exists())
        self.assertIn("priority_models", summary_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
