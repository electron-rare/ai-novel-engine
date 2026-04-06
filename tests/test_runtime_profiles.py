from __future__ import annotations

import unittest

from core.generation.provider import ProviderConfig
from core.runtime.config import openai_base_url_for_model, runtime_probe_profile
from core.runtime.health import probe_runtime_health
from core.runtime.profiles import runtime_probe_name, runtime_profile_name_for_model


class RuntimeProfileTests(unittest.TestCase):
    def test_provider_config_exposes_runtime_constraints_for_apple(self) -> None:
        profile = ProviderConfig(
            provider="openai_compatible",
            base_url="http://127.0.0.1:8100",
            api_key="",
            model="apple-coreml:qwen3.5-4b-onnx-q4f16",
            timeout=30.0,
            max_tokens=512,
            stage_max_tokens={},
        ).to_runtime_profile()

        self.assertTrue(profile.capabilities.requires_manual_model_switch)
        self.assertEqual(profile.capabilities.response_format_mode, "best_effort")
        self.assertEqual(profile.name, "apple_coreml_single_model")
        self.assertTrue(any(item.code == "manual-apple-switch" for item in profile.constraints))
        self.assertTrue(any(item.code == "json-best-effort" for item in profile.constraints))

    def test_runtime_profile_with_model_keeps_manual_switch_flag_for_cross_apple_switch(self) -> None:
        profile = ProviderConfig(
            provider="openai_compatible",
            base_url="http://127.0.0.1:8100",
            api_key="",
            model="apple-coreml:qwen2.5-0.5b-instruct-onnx",
            timeout=30.0,
            max_tokens=512,
            stage_max_tokens={},
        ).to_runtime_profile()

        updated = profile.with_model("apple-coreml:qwen3.5-4b-onnx-q4f16")
        self.assertTrue(updated.capabilities.requires_manual_model_switch)


class RuntimeHealthTests(unittest.TestCase):
    def test_probe_runtime_health_can_read_model_catalog(self) -> None:
        profile = ProviderConfig(
            provider="openai_compatible",
            base_url="http://127.0.0.1:8100",
            api_key="",
            model="ollama:qwen2.5:7b",
            timeout=30.0,
            max_tokens=512,
            stage_max_tokens={},
        ).to_runtime_profile()

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{\"status\": \"ok\"}'

        def fetch(url: str, timeout: float):
            if url.endswith("/v1/models"):
                return {"data": [{"id": "ollama:qwen2.5:7b"}]}
            raise AssertionError(url)

        health = probe_runtime_health(profile, opener=lambda *args, **kwargs: FakeResponse(), json_fetcher=fetch)
        self.assertTrue(health.ok)
        self.assertEqual(health.available_models, ["ollama:qwen2.5:7b"])

    def test_probe_runtime_health_reports_failure(self) -> None:
        profile = ProviderConfig(
            provider="openai_compatible",
            base_url="http://127.0.0.1:8100",
            api_key="",
            model="ollama:qwen2.5:7b",
            timeout=30.0,
            max_tokens=512,
            stage_max_tokens={},
        ).to_runtime_profile()

        health = probe_runtime_health(profile, opener=lambda *args, **kwargs: (_ for _ in ()).throw(OSError("down")))
        self.assertFalse(health.ok)
        self.assertIn("down", health.detail or "")


class RuntimeConfigHelpersTests(unittest.TestCase):
    def test_runtime_probe_profile_uses_runtime_probe_defaults(self) -> None:
        profile = runtime_probe_profile("http://127.0.0.1:8100", timeout=7.0)

        self.assertEqual(profile.base_url, "http://127.0.0.1:8100")
        self.assertEqual(profile.model, "runtime-probe")
        self.assertEqual(profile.timeout, 7.0)
        self.assertEqual(profile.name, "openai_probe")

    def test_openai_base_url_for_model_prefers_ollama_openai_runtime_when_enabled(self) -> None:
        self.assertEqual(
            openai_base_url_for_model(
                "ollama:qwen2.5:7b",
                core_base_url="http://127.0.0.1:8100",
                ollama_runtime="openai_compatible",
                ollama_openai_base_url="http://127.0.0.1:8091",
            ),
            "http://127.0.0.1:8091",
        )

    def test_openai_base_url_for_model_defaults_to_core_runtime(self) -> None:
        self.assertEqual(
            openai_base_url_for_model(
                "apple-coreml:qwen3.5-4b-onnx-q4f16",
                core_base_url="http://127.0.0.1:8100",
                ollama_runtime="openai_compatible",
                ollama_openai_base_url="http://127.0.0.1:8091",
            ),
            "http://127.0.0.1:8100",
        )

    def test_runtime_profile_name_for_model_maps_known_runtimes(self) -> None:
        self.assertEqual(runtime_profile_name_for_model("apple-coreml:qwen3.5-4b-onnx-q4f16"), "apple_coreml_single_model")
        self.assertEqual(runtime_profile_name_for_model("ollama:qwen2.5:7b"), "ollama_openai_compatible")
        self.assertEqual(
            runtime_profile_name_for_model("ollama:qwen2.5:7b", ollama_runtime="native"),
            "ollama_native",
        )

    def test_runtime_probe_name_maps_named_probe_profiles(self) -> None:
        self.assertEqual(runtime_probe_name("core"), "mascarade_local")
        self.assertEqual(runtime_probe_name("apple"), "apple_coreml_single_model")
        self.assertEqual(runtime_probe_name("ollama_openai"), "llama_cpp_local")
        self.assertEqual(
            runtime_probe_name("remote", base_url="http://tower.example.test:8100"),
            "mascarade_remote_tower_example_test",
        )
