#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
import plistlib
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.runtime.remote_hosts import RemoteHostConfig, read_remote_hosts

HostConfig = RemoteHostConfig


def _read_hosts(config_path: Path) -> list[HostConfig]:
    return read_remote_hosts(config_path, stderr=sys.stderr)


def _plist_payload(host: HostConfig) -> dict:
    return {
        "Label": host.label,
        "ProgramArguments": [
            "/usr/bin/ssh",
            "-N",
            "-o",
            "ExitOnForwardFailure=yes",
            "-o",
            "ServerAliveInterval=30",
            "-o",
            "ServerAliveCountMax=3",
            "-L",
            f"{host.local_bind_host}:{host.local_tunnel_port}:127.0.0.1:{host.remote_core_port}",
            host.ssh_target,
        ],
        "RunAtLoad": True,
        "KeepAlive": {"SuccessfulExit": False},
        "ProcessType": "Background",
    }


def _write_plists(hosts: list[HostConfig], launch_agents_dir: Path, dry_run: bool) -> list[Path]:
    paths: list[Path] = []
    for host in hosts:
        plist_path = launch_agents_dir / host.plist_name
        paths.append(plist_path)
        if dry_run:
            continue
        payload = _plist_payload(host)
        plist_path.parent.mkdir(parents=True, exist_ok=True)
        plist_path.write_bytes(plistlib.dumps(payload, fmt=plistlib.FMT_XML))
    return paths


def _run_launchctl(command: list[str], dry_run: bool) -> int:
    if dry_run:
        return 0
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"launchctl failed ({result.returncode}): {' '.join(command)}", file=sys.stderr)
        stderr = (result.stderr or "").strip()
        if stderr:
            print(stderr, file=sys.stderr)
    return result.returncode


def install(hosts: list[HostConfig], launch_agents_dir: Path, dry_run: bool) -> int:
    paths = _write_plists(hosts, launch_agents_dir, dry_run)
    failed = False
    for plist_path in paths:
        print(f"plist: {plist_path}")
        _run_launchctl(["launchctl", "unload", str(plist_path)], dry_run)
        if _run_launchctl(["launchctl", "load", str(plist_path)], dry_run) != 0:
            failed = True
    if dry_run:
        print("dry-run: aucun fichier ecrit et aucun launchctl execute")
    return 1 if failed else 0


def uninstall(hosts: list[HostConfig], launch_agents_dir: Path, dry_run: bool) -> int:
    for host in hosts:
        plist_path = launch_agents_dir / host.plist_name
        print(f"remove: {plist_path}")
        _run_launchctl(["launchctl", "unload", str(plist_path)], dry_run)
        if not dry_run and plist_path.exists():
            plist_path.unlink()
    return 0


def status(hosts: list[HostConfig]) -> int:
    uid = os.getuid()
    failed = False
    for host in hosts:
        print(host.label)
        result = subprocess.run(["launchctl", "print", f"gui/{uid}/{host.label}"], check=False)
        if result.returncode != 0:
            failed = True
    return 1 if failed else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 scripts/setup_mascarade_launchd.py")
    parser.add_argument("command", choices=["install", "uninstall", "render", "status"], help="Action a executer")
    parser.add_argument("--config", default="automation/mascarade_hosts.toml")
    parser.add_argument("--launch-agents-dir", default=str(Path.home() / "Library/LaunchAgents"))
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config_path = Path(args.config)
    launch_agents_dir = Path(args.launch_agents_dir).expanduser()

    hosts = _read_hosts(config_path)
    if not hosts:
        print("Aucun host valide trouve dans la config.")
        return 1

    if args.command == "install":
        return install(hosts, launch_agents_dir, args.dry_run)
    if args.command == "uninstall":
        return uninstall(hosts, launch_agents_dir, args.dry_run)
    if args.command == "status":
        return status(hosts)

    # render
    paths = _write_plists(hosts, launch_agents_dir, dry_run=True)
    for host, plist_path in zip(hosts, paths):
        print(f"[{host.name}] {plist_path}")
        print(plistlib.dumps(_plist_payload(host), fmt=plistlib.FMT_XML).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
