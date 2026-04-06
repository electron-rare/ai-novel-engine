from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
import tomllib
from typing import TextIO

from core.runtime.profiles import runtime_probe_name


@dataclass(frozen=True)
class RemoteHostConfig:
    name: str
    ssh_target: str
    local_tunnel_port: int
    remote_core_port: int
    remote_health_path: str
    local_bind_host: str
    ssh_connect_timeout_seconds: int

    def local_base_url(self) -> str:
        return f"http://{self.local_bind_host}:{self.local_tunnel_port}"

    def local_health_url(self) -> str:
        return f"{self.local_base_url()}{self.remote_health_path}"

    def tunnel_command(self) -> str:
        return (
            "ssh -N "
            "-o ExitOnForwardFailure=yes "
            "-o ServerAliveInterval=30 "
            "-o ServerAliveCountMax=3 "
            f"-L {self.local_bind_host}:{self.local_tunnel_port}:127.0.0.1:{self.remote_core_port} "
            f"{self.ssh_target}"
        )

    @property
    def label(self) -> str:
        return f"com.ai-novel-engine.mascarade.{self.name}.tunnel"

    @property
    def plist_name(self) -> str:
        return f"{self.label}.plist"

    def probe_profile_name(self) -> str:
        return runtime_probe_name("remote", remote_name=self.name)


def read_remote_hosts(config_path: Path, *, stderr: TextIO | None = None) -> list[RemoteHostConfig]:
    stderr = stderr or sys.stderr
    try:
        payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        print(f"Erreur lecture config {config_path}: {exc}", file=stderr)
        return []

    defaults = payload.get("defaults") if isinstance(payload, dict) else {}
    if not isinstance(defaults, dict):
        defaults = {}

    hosts = payload.get("hosts") if isinstance(payload, dict) else []
    if not isinstance(hosts, list):
        return []

    result: list[RemoteHostConfig] = []
    for raw in hosts:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name", "")).strip()
        ssh_target = str(raw.get("ssh_target", "")).strip()
        if not name or not ssh_target:
            continue

        local_tunnel_port = int(raw.get("local_tunnel_port", 0) or 0)
        if local_tunnel_port <= 0:
            continue

        result.append(
            RemoteHostConfig(
                name=name,
                ssh_target=ssh_target,
                local_tunnel_port=local_tunnel_port,
                remote_core_port=int(raw.get("remote_core_port", defaults.get("remote_core_port", 8100)) or 8100),
                remote_health_path=str(raw.get("remote_health_path", defaults.get("remote_health_path", "/health")) or "/health"),
                local_bind_host=str(raw.get("local_bind_host", defaults.get("local_bind_host", "127.0.0.1")) or "127.0.0.1"),
                ssh_connect_timeout_seconds=int(
                    raw.get("ssh_connect_timeout_seconds", defaults.get("ssh_connect_timeout_seconds", 4)) or 4
                ),
            )
        )

    return result
