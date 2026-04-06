from __future__ import annotations

import json
import unittest

from core.runtime.config import OpenAICompatibleRuntimeConfig, runtime_probe_profile
from core.runtime.health import probe_runtime_health, runtime_model_ids
from core.runtime.models import RuntimeProfile
from core.runtime.policies import (
    default_repair_fallback_model,
    is_cross_apple_runtime_switch,
    model_provider_name,
    resolve_repair_model,
)


class RuntimeConfigTests(unittest.TestCase):
    def test_runtime_profile_marks_apple_runtime_constraints(self):
        config = OpenAICompatibleRuntimeConfig.from_env(
            {
                "ANE_BASE_URL": "http://127.0.0.1:8100",
                "ANE_MODEL": "apple-coreml:qwen3.5-4b-onnx-q4f16",
            }
        )

        profile = config.to_runtime_profile()

        self.assertTrue(profile.capabilities.requires_manual_model_switch)
        self.assertTrue(profile.capabilities.single_model_per_runtime)
        codes = {item.code for item in profile.constraints}
        self.assertIn("apple_single_model_runtime", codes)

    def test_runtime_probe_profile_uses_shared_probe_defaults(self):
        profile = runtime_probe_profile("http://127.0.0.1:8100")

        self.assertEqual(profile.model, "runtime-probe")
        self.assertEqual(profile.max_tokens, 1)
        self.assertEqual(profile.timeout, 10.0)


class RuntimePoliciesTests(unittest.TestCase):
    def test_model_provider_name_extracts_prefix(self):
        self.assertEqual(model_provider_name("ollama:qwen2.5:7b"), "ollama")
        self.assertEqual(model_provider_name("apple-coreml:qwen3.5-4b-onnx-q4f16"), "apple-coreml")

    def test_default_repair_fallback_model_matches_known_runtime_defaults(self):
        self.assertEqual(default_repair_fallback_model("ollama:qwen2.5:1.5b"), "ollama:qwen2.5:7b")
        self.assertEqual(
            default_repair_fallback_model("apple-coreml:qwen3.5-4b-onnx-q4f16"),
            "ollama:qwen2.5:7b",
        )

    def test_cross_apple_runtime_switch_is_detected(self):
        self.assertTrue(
            is_cross_apple_runtime_switch(
                "apple-coreml:qwen2.5-0.5b-instruct-onnx",
                "apple-coreml:qwen3.5-4b-onnx-q4f16",
            )
        )

    def test_resolve_repair_model_keeps_same_provider_without_override(self):
        self.assertEqual(
            resolve_repair_model(
                base_model="apple-coreml:qwen3.5-4b-onnx-q4f16",
                attempt=2,
            ),
            "apple-coreml:qwen3.5-4b-onnx-q4f16",
        )

    def test_resolve_repair_model_rejects_cross_apple_override(self):
        with self.assertRaisesRegex(RuntimeError, "apple-coreml"):
            resolve_repair_model(
                base_model="apple-coreml:qwen2.5-0.5b-instruct-onnx",
                attempt=2,
                override_model="apple-coreml:qwen3.5-4b-onnx-q4f16",
            )


class RuntimeHealthTests(unittest.TestCase):
    def test_probe_runtime_health_reads_health_endpoint(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps({"status": "ok", "model": "apple-coreml:qwen3.5-4b-onnx-q4f16"}).encode("utf-8")

        profile = RuntimeProfile(
            provider="openai_compatible",
            base_url="http://127.0.0.1:8100",
            api_key="",
            model="apple-coreml:qwen3.5-4b-onnx-q4f16",
            timeout=5.0,
            max_tokens=256,
            stage_max_tokens={},
        )

        health = probe_runtime_health(profile, opener=lambda url, timeout: FakeResponse())

        self.assertTrue(health.ok)
        self.assertEqual(health.active_model, "apple-coreml:qwen3.5-4b-onnx-q4f16")
        self.assertEqual(health.status, "ok")

    def test_probe_runtime_health_reads_models_catalog_when_available(self):
        profile = RuntimeProfile(
            provider="openai_compatible",
            base_url="http://127.0.0.1:8100",
            api_key="",
            model="ollama:qwen2.5:7b",
            timeout=5.0,
            max_tokens=256,
            stage_max_tokens={},
        )

        def json_fetcher(url, timeout):
            self.assertTrue(url.endswith("/v1/models"))
            return {"data": [{"id": "ollama:qwen2.5:7b"}]}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps({"status": "ok"}).encode("utf-8")

        health = probe_runtime_health(
            profile,
            opener=lambda url, timeout: FakeResponse(),
            json_fetcher=json_fetcher,
        )

        self.assertTrue(health.ok)
        self.assertEqual(health.available_models, ["ollama:qwen2.5:7b"])

    def test_runtime_model_ids_flattens_ids_names_and_aliases(self):
        profile = runtime_probe_profile("http://127.0.0.1:8100")

        model_ids = runtime_model_ids(
            profile,
            json_fetcher=lambda _url, _timeout: {
                "data": [
                    {"id": "ollama:qwen2.5:7b", "aliases": ["qwen2.5:7b"]},
                    {"name": "apple-coreml:qwen3.5-4b-onnx-q4f16"},
                ],
                "models": ["fallback:model"],
            },
        )

        self.assertEqual(
            model_ids,
            {
                "ollama:qwen2.5:7b",
                "qwen2.5:7b",
                "apple-coreml:qwen3.5-4b-onnx-q4f16",
                "fallback:model",
            },
        )
