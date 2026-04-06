from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "setup_mascarade_launchd.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("setup_mascarade_launchd", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Impossible de charger setup_mascarade_launchd.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SetupMascaradeLaunchdTests(unittest.TestCase):
    def test_read_hosts_returns_empty_on_invalid_toml(self) -> None:
        module = _load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bad.toml"
            path.write_text("[[hosts]\nname='oops'", encoding="utf-8")
            hosts = module._read_hosts(path)
            self.assertEqual(hosts, [])

    def test_read_hosts_parses_valid_config(self) -> None:
        module = _load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "hosts.toml"
            path.write_text(
                "[defaults]\nremote_core_port = 8100\nlocal_bind_host = \"127.0.0.1\"\n"
                "[[hosts]]\nname = \"tower\"\nssh_target = \"clems@192.168.120\"\nlocal_tunnel_port = 8110\n",
                encoding="utf-8",
            )
            hosts = module._read_hosts(path)
            self.assertEqual(len(hosts), 1)
            self.assertEqual(hosts[0].name, "tower")
            self.assertEqual(hosts[0].label, "com.ai-novel-engine.mascarade.tower.tunnel")
            self.assertEqual(hosts[0].plist_name, "com.ai-novel-engine.mascarade.tower.tunnel.plist")


if __name__ == "__main__":
    unittest.main()
