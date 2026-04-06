from __future__ import annotations

import io
import json
import unittest
from urllib import error

from core.runtime.checkpoints import checkpoint_manual_action_for_model, host_port_from_base_url
from core.runtime.health import current_apple_model, wait_for_expected_apple_model
from core.runtime.preflight import ollama_base_url, run_ollama_native_preflight


class RuntimeCheckpointTests(unittest.TestCase):
    def test_checkpoint_manual_action_builds_apple_switch(self) -> None:
        action = checkpoint_manual_action_for_model(
            model="apple-coreml:qwen3.5-4b-onnx-q4f16",
            core_health_ok=True,
            ollama_runtime="openai_compatible",
            ollama_openai_runtime_ready=True,
            ollama_openai_base_url="http://127.0.0.1:8091",
            apple_model_active="qwen2.5-0.5b-instruct-onnx",
            repo_root="/repo",
            state_path="/repo/automation/state.json",
            ane_script_path="/repo/scripts/run_next_lots.py",
        )

        self.assertIsNotNone(action)
        assert action is not None
        self.assertIn("--apple-model", action.args)
        self.assertIn("qwen3.5-4b-onnx-q4f16", action.reason)

    def test_host_port_from_base_url_handles_https_default_port(self) -> None:
        self.assertEqual(host_port_from_base_url("https://example.test"), ("example.test", 443))


class AppleRuntimeHealthTests(unittest.TestCase):
    def test_current_apple_model_reads_first_model(self) -> None:
        model = current_apple_model(
            "http://127.0.0.1:8201",
            json_fetcher=lambda url, timeout: {"models": ["qwen3.5-4b-onnx-q4f16"]},
        )
        self.assertEqual(model, "qwen3.5-4b-onnx-q4f16")

    def test_wait_for_expected_apple_model_polls_until_match(self) -> None:
        payloads = iter(
            [
                {"models": ["qwen2.5-0.5b-instruct-onnx"]},
                {"models": ["qwen3.5-4b-onnx-q4f16"]},
            ]
        )
        ticks = iter([0.0, 0.0, 0.2, 0.4])

        model = wait_for_expected_apple_model(
            "http://127.0.0.1:8201",
            "qwen3.5-4b-onnx-q4f16",
            json_fetcher=lambda url, timeout: next(payloads),
            timeout_seconds=1.0,
            poll_interval_seconds=0.1,
            sleeper=lambda seconds: None,
            monotonic=lambda: next(ticks),
        )
        self.assertEqual(model, "qwen3.5-4b-onnx-q4f16")


class OllamaPreflightTests(unittest.TestCase):
    def test_ollama_base_url_removes_api_tags_suffix(self) -> None:
        self.assertEqual(ollama_base_url("http://127.0.0.1:11434/api/tags"), "http://127.0.0.1:11434")

    def test_run_ollama_native_preflight_returns_success_preview(self) -> None:
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps(
                    {
                        "model": "qwen2.5:7b",
                        "message": {"content": "ollama native preflight ok"},
                        "done_reason": "stop",
                    }
                ).encode("utf-8")

        result = run_ollama_native_preflight(
            model="qwen2.5:7b",
            tags_url="http://127.0.0.1:11434/api/tags",
            timeout_seconds=5.0,
            opener=lambda req, timeout: FakeResponse(),
            monotonic=lambda: 0.0,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("qwen2.5:7b", result.stdout)

    def test_run_ollama_native_preflight_reports_http_error(self) -> None:
        http_error = error.HTTPError(
            url="http://127.0.0.1:11434/api/chat",
            code=500,
            msg="boom",
            hdrs=None,
            fp=io.BytesIO(b"detail"),
        )

        result = run_ollama_native_preflight(
            model="qwen2.5:7b",
            tags_url="http://127.0.0.1:11434/api/tags",
            timeout_seconds=5.0,
            opener=lambda req, timeout: (_ for _ in ()).throw(http_error),
            monotonic=lambda: 0.0,
        )
        http_error.close()

        self.assertEqual(result.returncode, 1)
        self.assertIn("HTTP 500", result.stderr)
