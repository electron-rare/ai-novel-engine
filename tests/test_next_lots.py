from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from core.chapters import ChapterId
from core.next_lots import (
    AUTO_SYNC_TODO_ACTIVE,
    CommandResult,
    Manifest,
    ModelRunResult,
    NextLotsRunner,
    RunState,
    replace_auto_section,
)


class NextLotsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "ane"
        self.root.mkdir(parents=True, exist_ok=True)
        self.mascarade = Path(self.temp_dir.name) / "mascarade"
        self.mascarade.mkdir(parents=True, exist_ok=True)

        for path in (
            self.root / "README.md",
            self.root / "TODO_ACTIVE.md",
            self.root / "TODO_IMPLEMENTE.md",
            self.root / "docs" / "EXECUTION_PLAN_2026-03-08.md",
            self.root / "docs" / "MODEL_COMPARISON_2026-03-08.md",
            self.root / "docs" / "runbooks" / "LOCAL_GENERATION.md",
            self.mascarade / "README.md",
            self.mascarade / "TODO_AI_NOVEL_ENGINE.md",
            self.mascarade / "docs" / "EXECUTION_PLAN_2026-03-08.md",
            self.mascarade / "docs" / "RUNBOOK_APPLE_LLM_LOCAL.md",
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# {path.name}\n", encoding="utf-8")

        manifest_dir = self.root / "automation"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = manifest_dir / "next_lots.toml"
        self.manifest_path.write_text(
            (
                "[paths]\n"
                f"mascarade_repo = \"{self.mascarade}\"\n"
                "core_base_url = \"http://127.0.0.1:8100\"\n"
                "apple_runtime_url = \"http://127.0.0.1:8201\"\n"
                "ollama_tags_url = \"http://127.0.0.1:11435/api/tags\"\n\n"
                "apple_model_ready_timeout_seconds = 0\n"
                "apple_model_poll_interval_seconds = 0.01\n\n"
                "[smoke]\n"
                "chapter = \"02\"\n"
                "intention = \"Smoke intention\"\n"
                "timeout_seconds = 300\n\n"
                "[preset]\n"
                "ANE_MAX_TOKENS_STRUCTURE = \"256\"\n"
                "ANE_REPAIR_MAX_PASSES = \"2\"\n\n"
                "[ensure_models]\n"
                "apple_models = [\"qwen2.5-0.5b-instruct-onnx\", \"qwen3.5-4b-onnx-q4f16\", \"stateful-mistral7b-instruct-int4-coreml\"]\n"
                "ollama_models = [\"qwen2.5:7b\", \"qwen2.5:1.5b\"]\n\n"
                "[lots.priority_models]\n"
                "models = [\"apple-coreml:qwen3.5-4b-onnx-q4f16\", \"ollama:qwen2.5:7b\"]\n\n"
                "[lots.baselines]\n"
                "models = [\"apple-coreml:qwen2.5-0.5b-instruct-onnx\", \"ollama:qwen2.5:1.5b\"]\n\n"
                "[lots.preflight_only]\n"
                "models = [\"apple-coreml:stateful-mistral7b-instruct-int4-coreml\"]\n\n"
                "[tracking.ane]\n"
                "todo_active = \"TODO_ACTIVE.md\"\n"
                "todo_done = \"TODO_IMPLEMENTE.md\"\n"
                "plan = \"docs/EXECUTION_PLAN_2026-03-08.md\"\n"
                "comparison = \"docs/MODEL_COMPARISON_2026-03-08.md\"\n"
                "readme = \"README.md\"\n"
                "runbook = \"docs/runbooks/LOCAL_GENERATION.md\"\n\n"
                "[tracking.mascarade]\n"
                "todo = \"TODO_AI_NOVEL_ENGINE.md\"\n"
                "plan = \"docs/EXECUTION_PLAN_2026-03-08.md\"\n"
                "readme = \"README.md\"\n"
                "runbook = \"docs/RUNBOOK_APPLE_LLM_LOCAL.md\"\n\n"
                "[next_actions]\n"
                "rewrite_compaction = \"Compacter rewrite\"\n"
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_manifest_loads_tracking_and_models(self) -> None:
        manifest = Manifest.load(self.root, self.manifest_path)

        self.assertEqual(manifest.priority_models, ["apple-coreml:qwen3.5-4b-onnx-q4f16", "ollama:qwen2.5:7b"])
        self.assertEqual(manifest.required_apple_models[0], "qwen2.5-0.5b-instruct-onnx")
        self.assertEqual(manifest.tracking.mascarade_repo, self.mascarade)
        self.assertEqual(manifest.tracking.ane_todo_active, self.root / "TODO_ACTIVE.md")
        self.assertEqual(manifest.apple_model_ready_timeout_seconds, 0)

    def test_replace_auto_section_only_replaces_managed_block(self) -> None:
        path = self.root / "TODO_ACTIVE.md"
        path.write_text(
            "# Manual\n\n"
            "Avant.\n\n"
            "## Auto-sync\n"
            "<!-- AUTO-SYNC:ANE-TODO-ACTIVE:START -->\n"
            "ancien\n"
            "<!-- AUTO-SYNC:ANE-TODO-ACTIVE:END -->\n\n"
            "Apres.\n",
            encoding="utf-8",
        )

        replace_auto_section(path, AUTO_SYNC_TODO_ACTIVE, "## Auto-sync", "- nouveau")
        rendered = path.read_text(encoding="utf-8")

        self.assertIn("Avant.", rendered)
        self.assertIn("Apres.", rendered)
        self.assertIn("- nouveau", rendered)
        self.assertNotIn("ancien", rendered)

    def test_runner_creates_checkpoint_when_apple_model_differs(self) -> None:
        manifest = Manifest.load(self.root, self.manifest_path)
        prepare_calls: list[list[str]] = []

        def command_runner(args: list[str], cwd: Path, env=None) -> CommandResult:
            if "prepare_runtime_step.sh" in " ".join(args):
                prepare_calls.append(args)
            return CommandResult(args=args, returncode=0, stdout="prepared", stderr="", duration_seconds=0.1)

        def json_fetcher(url: str, timeout: float):
            if url.endswith("/health"):
                return {"status": "ok"}
            if url.endswith("/models"):
                return ["qwen2.5-0.5b-instruct-onnx"]
            raise AssertionError(url)

        runner = NextLotsRunner(manifest, command_runner=command_runner, json_fetcher=json_fetcher)
        exit_code = runner.run(lot="priority_models")

        self.assertEqual(exit_code, 3)
        self.assertEqual(len(prepare_calls), 1)
        self.assertIn("--apple-model", prepare_calls[0])
        state = RunState.load(self.root / "automation" / "state" / "next_lots_state.json")
        self.assertIsNotNone(state.pending_manual_action)
        self.assertIn("qwen3.5-4b-onnx-q4f16", state.pending_manual_action["reason"])

    def test_runner_waits_for_apple_model_before_checkpointing(self) -> None:
        manifest = Manifest.load(self.root, self.manifest_path)
        manifest = Manifest(
            **{
                **manifest.__dict__,
                "apple_model_ready_timeout_seconds": 0.05,
                "apple_model_poll_interval_seconds": 0.0,
            }
        )
        prepare_calls: list[list[str]] = []
        model_calls = {"count": 0}

        def command_runner(args: list[str], cwd: Path, env=None) -> CommandResult:
            if "prepare_runtime_step.sh" in " ".join(args):
                prepare_calls.append(args)
            return CommandResult(args=args, returncode=0, stdout="prepared", stderr="", duration_seconds=0.1)

        def json_fetcher(url: str, timeout: float):
            if url.endswith("/health"):
                return {"status": "ok"}
            if url.endswith("/models"):
                model_calls["count"] += 1
                if model_calls["count"] == 1:
                    return {"models": []}
                return ["qwen3.5-4b-onnx-q4f16"]
            raise AssertionError(url)

        runner = NextLotsRunner(manifest, command_runner=command_runner, json_fetcher=json_fetcher)
        checkpoint = runner._checkpoint_if_runtime_manual_step_needed(
            RunState.new(
                manifest,
                lot="priority_models",
                report_dir=self.root / "automation" / "reports" / "sync",
                state_path=self.root / "automation" / "state" / "next_lots_state.json",
                steps=[{"type": "models", "name": "priority_models", "models": manifest.priority_models, "preflight_only": False}],
            ),
            "apple-coreml:qwen3.5-4b-onnx-q4f16",
        )

        self.assertIsNone(checkpoint)
        self.assertEqual(prepare_calls, [])
        self.assertGreaterEqual(model_calls["count"], 2)

    def test_run_model_classifies_accepted_from_meta(self) -> None:
        manifest = Manifest.load(self.root, self.manifest_path)
        chapter = ChapterId.parse("02")

        def command_runner(args: list[str], cwd: Path, env=None) -> CommandResult:
            if "smoke_openai_compat_ane.sh" in " ".join(args):
                return CommandResult(args=args, returncode=0, stdout="ok", stderr="", duration_seconds=0.2)
            if "smoke_local_generation.sh" in " ".join(args):
                workspace = Path(args[args.index("--workspace") + 1])
                meta_path = workspace / "brouillons" / "chapitres" / chapter.slug / "meta.json"
                meta_path.parent.mkdir(parents=True, exist_ok=True)
                meta_path.write_text(
                    json.dumps(
                        {
                            "status": "accepted",
                            "accepted": True,
                            "completed_stages": ["structure", "draft", "critique", "rewrite", "gate", "memory"],
                            "retry_stages": ["gate"],
                            "repair_attempts": 1,
                            "repair_models": ["ollama:qwen2.5:7b"],
                            "artifacts": {
                                "repair_latest": str(meta_path.parent / "repair_v1.md"),
                                "gate_v1": str(meta_path.parent / "gate_v1.json"),
                                "manuscript": str(workspace / "manuscrit" / chapter.filename),
                            },
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                return CommandResult(args=args, returncode=0, stdout="smoke ok", stderr="", duration_seconds=1.5)
            raise AssertionError(args)

        runner = NextLotsRunner(
            manifest,
            command_runner=command_runner,
            json_fetcher=lambda url, timeout: {"status": "ok"} if url.endswith("/health") else ["qwen3.5-4b-onnx-q4f16"],
        )
        report_dir = self.root / "automation" / "reports" / "test"
        report_dir.mkdir(parents=True, exist_ok=True)
        result = runner._run_model("ollama:qwen2.5:7b", category="priority_models", preflight_only=False, report_dir=report_dir)

        self.assertEqual(result.classification, "accepted")
        self.assertEqual(result.repair_attempts, 1)
        self.assertIn("gate", result.completed_stages)

    def test_tracking_sync_updates_docs_with_auto_sync_sections(self) -> None:
        manifest = Manifest.load(self.root, self.manifest_path)
        runner = NextLotsRunner(
            manifest,
            command_runner=lambda args, cwd, env=None: CommandResult(args=args, returncode=0, stdout="", stderr="", duration_seconds=0.0),
            json_fetcher=lambda url, timeout: {"status": "ok"},
        )
        state = RunState.new(
            manifest,
            lot="tracking_sync",
            report_dir=self.root / "automation" / "reports" / "sync",
            state_path=self.root / "automation" / "state" / "next_lots_state.json",
            steps=[{"type": "tracking_sync"}],
        )
        state.results = [
            asdict(
                ModelRunResult(
                    model="ollama:qwen2.5:7b",
                    category="priority_models",
                    classification="provider_failed",
                    preflight_ok=True,
                    smoke_attempted=True,
                    status="failed",
                    failed_stage="rewrite",
                )
            )
        ]

        runner._sync_tracking(state, dry_run=False)

        self.assertIn("AUTO-SYNC:ANE-TODO-ACTIVE:START", (self.root / "TODO_ACTIVE.md").read_text(encoding="utf-8"))
        self.assertIn("Compacter rewrite", (self.root / "docs" / "EXECUTION_PLAN_2026-03-08.md").read_text(encoding="utf-8"))
        self.assertIn("ollama:qwen2.5:7b", (self.root / "docs" / "MODEL_COMPARISON_2026-03-08.md").read_text(encoding="utf-8"))


def asdict(result: ModelRunResult) -> dict[str, object]:
    return {
        "model": result.model,
        "category": result.category,
        "classification": result.classification,
        "preflight_ok": result.preflight_ok,
        "preflight_duration_seconds": result.preflight_duration_seconds,
        "smoke_attempted": result.smoke_attempted,
        "smoke_duration_seconds": result.smoke_duration_seconds,
        "status": result.status,
        "accepted": result.accepted,
        "failed_stage": result.failed_stage,
        "quality_blockers": result.quality_blockers,
        "retry_stages": result.retry_stages,
        "repair_attempts": result.repair_attempts,
        "repair_models": result.repair_models,
        "draft_path": result.draft_path,
        "gate_path": result.gate_path,
        "meta_path": result.meta_path,
        "manuscript_path": result.manuscript_path,
        "notes": result.notes,
        "preflight_log": result.preflight_log,
        "smoke_log": result.smoke_log,
        "workspace": result.workspace,
        "apple_model_active": result.apple_model_active,
        "completed_stages": result.completed_stages,
    }
