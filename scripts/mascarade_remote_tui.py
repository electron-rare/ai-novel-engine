#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import time
from urllib import error as urllib_error, request as urllib_request

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.runtime.config import runtime_probe_profile
from core.runtime.health import probe_runtime_health
from core.runtime.remote_hosts import RemoteHostConfig, read_remote_hosts


def _short(value: str, width: int) -> str:
    if len(value) <= width:
        return value
    if width <= 3:
        return value[:width]
    return value[: width - 3] + "..."


def _http_probe(url: str, timeout: float = 1.5) -> str:
    try:
        with urllib_request.urlopen(url, timeout=timeout) as response:
            return f"UP ({response.status})"
    except urllib_error.HTTPError as error:
        return f"UP ({error.code})"
    except (urllib_error.URLError, OSError, ValueError):
        return "DOWN"


def _run_ssh_probe(target: str, timeout_seconds: int) -> str:
    cmd = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        f"ConnectTimeout={max(1, timeout_seconds)}",
        target,
        "echo",
        "ok",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=max(2, timeout_seconds + 1), check=False)
    except (subprocess.SubprocessError, OSError, ValueError):
        return "DOWN"

    if result.returncode == 0 and result.stdout.strip() == "ok":
        return "UP"
    return "DOWN"


def _probe_remote_runtime(host: RemoteHostConfig, timeout: float = 1.5) -> tuple[bool, str | None]:
    profile = runtime_probe_profile(
        host.local_base_url(),
        timeout=timeout,
        name=host.probe_profile_name(),
    )
    health = probe_runtime_health(profile)
    return health.ok, health.active_model


def _render(config_path: Path, hosts: list[RemoteHostConfig]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    lines: list[str] = []

    lines.append("Mascarade Remote TUI")
    lines.append(f"utc now: {now}")
    lines.append(f"config: {config_path}")
    lines.append("")

    if not hosts:
        lines.append("Aucun host valide dans la config.")
        lines.append("Attendu: [[hosts]] avec name, ssh_target, local_tunnel_port.")
        return "\n".join(lines)

    lines.append("etat remote:")
    for host in hosts:
        ssh_status = _run_ssh_probe(host.ssh_target, host.ssh_connect_timeout_seconds)
        local_http_status = _http_probe(host.local_health_url())
        runtime_ok, active_model = _probe_remote_runtime(host)
        runtime_status = "UP" if runtime_ok else "DOWN"
        if active_model:
            runtime_status += f" model={active_model}"

        lines.append(
            "- {name}: ssh={ssh} | tunnel={tunnel} | runtime={runtime} | target={target}".format(
                name=host.name,
                ssh=ssh_status,
                tunnel=local_http_status,
                runtime=runtime_status,
                target=_short(host.ssh_target, 40),
            )
        )
        lines.append(f"  local url: {host.local_health_url()}")
        lines.append(f"  profile: {host.probe_profile_name()}")
        lines.append(f"  tunnel cmd: {host.tunnel_command()}")
        lines.append(f"  launchd: {host.label}")

        if ssh_status != "UP":
            lines.append(f"  next: verifier cle/VPN puis tester `ssh {host.ssh_target} echo ok`")
        elif local_http_status == "DOWN":
            lines.append(f"  next: lancer `{host.tunnel_command()}`")
            lines.append(
                "  next: ou relancer launchd `launchctl kickstart -k "
                f"gui/$(id -u)/{host.label}`"
            )
        elif not runtime_ok:
            lines.append("  next: tunnel OK mais runtime distant indisponible; verifier Mascarade sur l'hote remote")
        else:
            lines.append("  next: OK - tunnel utilisable")

    lines.append("")
    lines.append("actions utiles:")
    lines.append("- python3 scripts/reports_ops.py analyze-logs --top 12")
    lines.append("- python3 scripts/reports_ops.py prune --days 14 --delete-workspaces")
    lines.append("- python3 scripts/reports_ops.py prune --days 14 --delete-workspaces --apply")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 scripts/mascarade_remote_tui.py")
    parser.add_argument("--config", default="automation/mascarade_hosts.toml")
    parser.add_argument("--watch", action="store_true", help="Rafraichit en boucle la vue TUI.")
    parser.add_argument("--interval", type=float, default=4.0, help="Intervalle de rafraichissement en secondes.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config_path = Path(args.config)

    def draw_once() -> None:
        hosts = read_remote_hosts(config_path)
        print(_render(config_path, hosts))

    if args.watch:
        interval = max(0.5, float(args.interval))
        try:
            while True:
                print("\033[2J\033[H", end="")
                draw_once()
                time.sleep(interval)
        except KeyboardInterrupt:
            return 0
    else:
        draw_once()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
