from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

from core.runtime.models import RuntimeHealth
from core.runtime.remote_hosts import RemoteHostConfig, read_remote_hosts


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "mascarade_remote_tui.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("mascarade_remote_tui", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Impossible de charger mascarade_remote_tui.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RemoteHostsTests(unittest.TestCase):
    def test_read_remote_hosts_parses_defaults_and_remote_profile_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "hosts.toml"
            path.write_text(
                "[defaults]\nremote_core_port = 8100\nlocal_bind_host = \"127.0.0.1\"\n"
                "[[hosts]]\nname = \"tower\"\nssh_target = \"clems@192.168.120\"\nlocal_tunnel_port = 8110\n",
                encoding="utf-8",
            )
            hosts = read_remote_hosts(path)

        self.assertEqual(len(hosts), 1)
        self.assertEqual(hosts[0].local_base_url(), "http://127.0.0.1:8110")
        self.assertEqual(hosts[0].probe_profile_name(), "mascarade_remote_tower")


class MascaradeRemoteTuiTests(unittest.TestCase):
    def test_probe_remote_runtime_builds_named_profile(self) -> None:
        module = _load_module()
        host = RemoteHostConfig(
            name="tower",
            ssh_target="clems@192.168.120",
            local_tunnel_port=8110,
            remote_core_port=8100,
            remote_health_path="/health",
            local_bind_host="127.0.0.1",
            ssh_connect_timeout_seconds=4,
        )
        captured: dict[str, str] = {}

        def fake_probe(profile):
            captured["name"] = profile.name
            captured["base_url"] = profile.base_url
            return RuntimeHealth(ok=True, url=profile.base_url, active_model="apple-coreml:qwen3.5-4b-onnx-q4f16")

        module.probe_runtime_health = fake_probe
        ok, active_model = module._probe_remote_runtime(host)

        self.assertTrue(ok)
        self.assertEqual(active_model, "apple-coreml:qwen3.5-4b-onnx-q4f16")
        self.assertEqual(captured["name"], "mascarade_remote_tower")
        self.assertEqual(captured["base_url"], "http://127.0.0.1:8110")

    def test_render_shows_profile_and_active_model_when_runtime_is_up(self) -> None:
        module = _load_module()
        host = RemoteHostConfig(
            name="tower",
            ssh_target="clems@192.168.120",
            local_tunnel_port=8110,
            remote_core_port=8100,
            remote_health_path="/health",
            local_bind_host="127.0.0.1",
            ssh_connect_timeout_seconds=4,
        )
        module._run_ssh_probe = lambda *_args, **_kwargs: "UP"
        module._http_probe = lambda *_args, **_kwargs: "UP (200)"
        module._probe_remote_runtime = lambda *_args, **_kwargs: (True, "ollama:qwen2.5:7b")

        rendered = module._render(Path("automation/mascarade_hosts.toml"), [host])

        self.assertIn("profile: mascarade_remote_tower", rendered)
        self.assertIn("runtime=UP model=ollama:qwen2.5:7b", rendered)

    def test_render_keeps_tunnel_guidance_when_tunnel_is_down(self) -> None:
        module = _load_module()
        host = RemoteHostConfig(
            name="tower",
            ssh_target="clems@192.168.120",
            local_tunnel_port=8110,
            remote_core_port=8100,
            remote_health_path="/health",
            local_bind_host="127.0.0.1",
            ssh_connect_timeout_seconds=4,
        )
        module._run_ssh_probe = lambda *_args, **_kwargs: "UP"
        module._http_probe = lambda *_args, **_kwargs: "DOWN"
        module._probe_remote_runtime = lambda *_args, **_kwargs: (False, None)

        rendered = module._render(Path("automation/mascarade_hosts.toml"), [host])

        self.assertIn("next: lancer `ssh -N", rendered)
        self.assertIn("launchctl kickstart -k", rendered)


if __name__ == "__main__":
    unittest.main()
