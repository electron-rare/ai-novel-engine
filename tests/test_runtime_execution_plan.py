from __future__ import annotations

import unittest

from core.runtime.orchestration import (
    RuntimeCheckpointSignals,
    build_runtime_execution_plan,
    collect_checkpoint_runtime_signals,
    missing_ollama_models,
    openai_runtime_model_ids,
    runtime_timeout_for_model,
)


class RuntimeExecutionPlanTests(unittest.TestCase):
    def test_build_runtime_execution_plan_for_apple_uses_core_runtime_and_long_timeout(self) -> None:
        plan = build_runtime_execution_plan(
            "apple-coreml:qwen3.5-4b-onnx-q4f16",
            core_base_url="http://127.0.0.1:8100",
            ollama_runtime="native",
            ollama_openai_base_url="http://127.0.0.1:8091",
            smoke_timeout_seconds=300,
        )

        self.assertEqual(plan.openai_base_url, "http://127.0.0.1:8100")
        self.assertEqual(plan.timeout_seconds, 600)
        self.assertFalse(plan.requires_native_ollama_preflight)
        self.assertEqual(plan.probe_profile_name, "mascarade_local")

    def test_build_runtime_execution_plan_for_native_ollama_requires_native_preflight(self) -> None:
        plan = build_runtime_execution_plan(
            "ollama:qwen2.5:7b",
            core_base_url="http://127.0.0.1:8100",
            ollama_runtime="native",
            ollama_openai_base_url="http://127.0.0.1:8091",
            smoke_timeout_seconds=300,
        )

        self.assertTrue(plan.requires_native_ollama_preflight)
        self.assertEqual(plan.openai_base_url, "http://127.0.0.1:8100")

    def test_build_runtime_execution_plan_for_openai_compatible_ollama_uses_llama_cpp_url(self) -> None:
        plan = build_runtime_execution_plan(
            "ollama:qwen2.5:7b",
            core_base_url="http://127.0.0.1:8100",
            ollama_runtime="openai_compatible",
            ollama_openai_base_url="http://127.0.0.1:8091",
            smoke_timeout_seconds=300,
        )

        self.assertFalse(plan.requires_native_ollama_preflight)
        self.assertEqual(plan.openai_base_url, "http://127.0.0.1:8091")
        self.assertEqual(plan.probe_profile_name, "llama_cpp_local")

    def test_runtime_timeout_for_model_keeps_apple_high_and_others_medium(self) -> None:
        self.assertEqual(runtime_timeout_for_model("apple-coreml:model", smoke_timeout_seconds=300), 600)
        self.assertEqual(runtime_timeout_for_model("ollama:model", smoke_timeout_seconds=90), 120)


class RuntimeSignalsTests(unittest.TestCase):
    def test_collect_checkpoint_runtime_signals_for_apple_waits_and_reports_core_health(self) -> None:
        calls: list[str] = []

        def fetch(url: str, timeout: float):
            calls.append(url)
            if url == "http://127.0.0.1:8100/health":
                return {"status": "ok"}
            if url == "http://127.0.0.1:8100/v1/models":
                return {"data": [{"id": "apple-coreml:qwen3.5-4b-onnx-q4f16"}]}
            if url == "http://127.0.0.1:8201/models":
                return {"models": ["qwen3.5-4b-onnx-q4f16"]}
            raise AssertionError(url)

        signals = collect_checkpoint_runtime_signals(
            "apple-coreml:qwen3.5-4b-onnx-q4f16",
            core_base_url="http://127.0.0.1:8100",
            apple_runtime_url="http://127.0.0.1:8201",
            apple_model_ready_timeout_seconds=0.0,
            apple_model_poll_interval_seconds=0.0,
            ollama_runtime="native",
            ollama_openai_base_url="http://127.0.0.1:8091",
            json_fetcher=fetch,
        )

        self.assertEqual(
            signals,
            RuntimeCheckpointSignals(
                core_health_ok=True,
                apple_model_active="qwen3.5-4b-onnx-q4f16",
                ollama_openai_runtime_ready=False,
            ),
        )
        self.assertIn("http://127.0.0.1:8201/models", calls)

    def test_collect_checkpoint_runtime_signals_marks_openai_compatible_ollama_ready(self) -> None:
        def fetch(url: str, timeout: float):
            if url == "http://127.0.0.1:8100/health":
                return {"status": "ok"}
            if url == "http://127.0.0.1:8100/v1/models":
                return {"data": [{"id": "apple-coreml:qwen3.5-4b-onnx-q4f16"}]}
            if url == "http://127.0.0.1:8091/health":
                return {"status": "ok"}
            if url == "http://127.0.0.1:8091/v1/models":
                return {"data": [{"id": "sha256-demo", "aliases": ["ollama:qwen2.5:7b"]}]}
            raise AssertionError(url)

        signals = collect_checkpoint_runtime_signals(
            "ollama:qwen2.5:7b",
            core_base_url="http://127.0.0.1:8100",
            apple_runtime_url="http://127.0.0.1:8201",
            apple_model_ready_timeout_seconds=0.0,
            apple_model_poll_interval_seconds=0.0,
            ollama_runtime="openai_compatible",
            ollama_openai_base_url="http://127.0.0.1:8091",
            json_fetcher=fetch,
        )

        self.assertEqual(
            signals,
            RuntimeCheckpointSignals(
                core_health_ok=True,
                apple_model_active=None,
                ollama_openai_runtime_ready=True,
            ),
        )

    def test_openai_runtime_model_ids_can_fall_back_to_health_available_models(self) -> None:
        import core.runtime.orchestration as module

        original = module.runtime_model_ids
        module.runtime_model_ids = lambda _profile, json_fetcher: (_ for _ in ()).throw(ValueError("boom"))
        try:
            model_ids = openai_runtime_model_ids(
                "http://127.0.0.1:8091",
                json_fetcher=lambda url, timeout: {"status": "ok"} if url.endswith("/health") else {"data": [{"id": "ollama:qwen2.5:7b"}]},
                profile_name="llama_cpp_local",
            )
        finally:
            module.runtime_model_ids = original

        self.assertEqual(model_ids, {"ollama:qwen2.5:7b"})

    def test_missing_ollama_models_reads_tag_catalog(self) -> None:
        missing = missing_ollama_models(
            ["qwen2.5:7b", "qwen2.5:1.5b"],
            tags_url="http://127.0.0.1:11434/api/tags",
            json_fetcher=lambda _url, _timeout: {"models": [{"name": "qwen2.5:7b"}]},
        )

        self.assertEqual(missing, ["qwen2.5:1.5b"])


if __name__ == "__main__":
    unittest.main()
