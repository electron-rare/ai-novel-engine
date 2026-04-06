#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

chapter="02"
workspace=""
base_url="${ANE_BASE_URL:-http://127.0.0.1:8100}"
model="${ANE_MODEL:-}"
timeout="${ANE_TIMEOUT:-}"
decision="approve"
intention="Chapitre court. Une femme arrive dans une ville de nuit, trouve un indice simple, et finit sur une decision risquee. Style direct, phrases courtes, ton sobre."

usage() {
  cat <<'EOF'
Usage:
  ./scripts/smoke_local_generation.sh [options]

Options:
  --chapter N         Chapter number to generate (default: 02)
  --workspace DIR     Reuse or create the smoke workspace in DIR
  --intention TEXT    Override the default smoke intention
  --base-url URL      OpenAI-compatible base URL (default: ANE_BASE_URL or http://127.0.0.1:8100)
  --model MODEL       Explicit model in provider:model format (required unless ANE_MODEL is already set)
  --timeout SEC       Provider timeout in seconds (default: 900 for apple-coreml, 300 otherwise)
  --approve           Promote without interactive prompt (default)
  --reject            Reject without interactive prompt
  --no-approve        Deprecated alias for --reject
  -h, --help          Show this help

Environment:
  ANE_BASE_URL        Used if --base-url is not provided
  ANE_MODEL           Used if --model is not provided
  ANE_TIMEOUT         Default: 900 for apple-coreml, 300 otherwise
  ANE_MAX_TOKENS      Default: 192 for apple-coreml, 384 otherwise
  ANE_MAX_TOKENS_STRUCTURE Default: 96 for apple-coreml, 224 otherwise
  ANE_MAX_TOKENS_DRAFT     Default: 192 for apple-coreml, 384 otherwise
  ANE_MAX_TOKENS_CRITIQUE  Default: 160 for apple-coreml, 512 otherwise
  ANE_MAX_TOKENS_REWRITE   Default: 192 for apple-coreml, 1024 otherwise
  ANE_MAX_TOKENS_GATE      Default: 128 for apple-coreml, 384 otherwise
  ANE_MAX_TOKENS_REPAIR    Default: 160 for apple-coreml, 1536 otherwise
  ANE_MAX_TOKENS_MEMORY    Default: 128 for apple-coreml, 320 otherwise
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --chapter)
      chapter="${2:-}"
      shift 2
      ;;
    --workspace)
      workspace="${2:-}"
      shift 2
      ;;
    --intention)
      intention="${2:-}"
      shift 2
      ;;
    --base-url)
      base_url="${2:-}"
      shift 2
      ;;
    --model)
      model="${2:-}"
      shift 2
      ;;
    --timeout)
      timeout="${2:-}"
      shift 2
      ;;
    --approve)
      decision="approve"
      shift
      ;;
    --reject|--no-approve)
      decision="reject"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "${model}" ]]; then
  echo "ANE model required. Pass --model provider:model or export ANE_MODEL." >&2
  exit 2
fi

if [[ -z "${workspace}" ]]; then
  workspace="$(mktemp -d "${TMPDIR:-/tmp}/ane-local-smoke.XXXXXX")"
fi

mkdir -p "${workspace}"

if [[ -z "${timeout}" ]]; then
  if [[ "${model}" == apple-coreml:* ]]; then
    timeout="900"
  else
    timeout="300"
  fi
fi

if [[ "${model}" == apple-coreml:* ]]; then
  export ANE_MAX_TOKENS="${ANE_MAX_TOKENS:-192}"
  export ANE_MAX_TOKENS_STRUCTURE="${ANE_MAX_TOKENS_STRUCTURE:-96}"
  export ANE_MAX_TOKENS_DRAFT="${ANE_MAX_TOKENS_DRAFT:-192}"
  export ANE_MAX_TOKENS_CRITIQUE="${ANE_MAX_TOKENS_CRITIQUE:-160}"
  export ANE_MAX_TOKENS_REWRITE="${ANE_MAX_TOKENS_REWRITE:-192}"
  export ANE_MAX_TOKENS_GATE="${ANE_MAX_TOKENS_GATE:-128}"
  export ANE_MAX_TOKENS_REPAIR="${ANE_MAX_TOKENS_REPAIR:-160}"
  export ANE_MAX_TOKENS_MEMORY="${ANE_MAX_TOKENS_MEMORY:-128}"
else
  export ANE_MAX_TOKENS="${ANE_MAX_TOKENS:-384}"
  export ANE_MAX_TOKENS_STRUCTURE="${ANE_MAX_TOKENS_STRUCTURE:-224}"
  export ANE_MAX_TOKENS_DRAFT="${ANE_MAX_TOKENS_DRAFT:-384}"
  export ANE_MAX_TOKENS_CRITIQUE="${ANE_MAX_TOKENS_CRITIQUE:-512}"
  export ANE_MAX_TOKENS_REWRITE="${ANE_MAX_TOKENS_REWRITE:-1024}"
  export ANE_MAX_TOKENS_GATE="${ANE_MAX_TOKENS_GATE:-384}"
  export ANE_MAX_TOKENS_REPAIR="${ANE_MAX_TOKENS_REPAIR:-1536}"
  export ANE_MAX_TOKENS_MEMORY="${ANE_MAX_TOKENS_MEMORY:-320}"
fi

export ANE_PROVIDER="${ANE_PROVIDER:-openai_compatible}"
export ANE_BASE_URL="${base_url}"
export ANE_MODEL="${model}"
export ANE_TIMEOUT="${timeout}"

warmup_openai_compatible() {
  python3 - <<'PY'
from __future__ import annotations

import json
import os
import socket
import sys
import urllib.request

base_url = os.environ["ANE_BASE_URL"].rstrip("/")
if base_url.endswith("/v1"):
    url = f"{base_url}/chat/completions"
elif base_url.endswith("/chat/completions"):
    url = base_url
else:
    url = f"{base_url}/v1/chat/completions"

payload = {
    "model": os.environ["ANE_MODEL"],
    "messages": [{"role": "user", "content": "Respond with exactly: ok"}],
    "temperature": 0,
    "max_tokens": 8,
}
body = json.dumps(payload).encode("utf-8")
headers = {"Content-Type": "application/json"}
api_key = os.environ.get("ANE_API_KEY", "").strip()
if api_key:
    headers["Authorization"] = f"Bearer {api_key}"

request = urllib.request.Request(url, data=body, headers=headers, method="POST")
try:
    with urllib.request.urlopen(request, timeout=float(os.environ.get("ANE_TIMEOUT", "300"))) as response:
        payload = json.loads(response.read().decode("utf-8"))
except (TimeoutError, socket.timeout) as exc:
    print(f"Warm-up OpenAI-compatible failed: timeout after {os.environ.get('ANE_TIMEOUT', '300')}s", file=sys.stderr)
    raise SystemExit(1) from exc

content = payload["choices"][0]["message"]["content"]
print(f"Warm-up OpenAI-compatible OK: {content}")
PY
}

prepare_workspace() {
  python3 - <<'PY'
from __future__ import annotations

from pathlib import Path
import os

from core.chapters import ChapterId

root = Path(os.environ["ANE_SMOKE_ROOT"])
chapter_id = ChapterId.parse(os.environ["ANE_SMOKE_CHAPTER"])
intention = os.environ["ANE_SMOKE_INTENTION"].strip()

intentions_dir = root / "notes" / "intentions"
intentions_dir.mkdir(parents=True, exist_ok=True)
intention_path = intentions_dir / chapter_id.filename
if not intention_path.exists():
    intention_path.write_text(
        f"# Intention — Chapitre {chapter_id.label}\n\n{intention}\n",
        encoding="utf-8",
    )
PY
}

print_summary() {
  python3 - <<'PY'
from __future__ import annotations

from pathlib import Path
import json
import os
import sys

from core.chapters import ChapterId

root = Path(os.environ["ANE_SMOKE_ROOT"])
chapter_id = ChapterId.parse(os.environ["ANE_SMOKE_CHAPTER"])
meta_path = root / "brouillons" / "chapitres" / chapter_id.slug / "meta.json"

print("")
print("Smoke summary")
print(f"- workspace: {root}")
print(f"- model: {os.environ['ANE_MODEL']}")
print(f"- chapter: {chapter_id.slug}")

if not meta_path.exists():
    print("- meta: absent")
    sys.exit(0)

meta = json.loads(meta_path.read_text(encoding="utf-8"))
print(f"- status: {meta.get('status')}")
print(f"- accepted: {meta.get('accepted')}")
if meta.get("failed_stage"):
    print(f"- failed_stage: {meta.get('failed_stage')}")
quality_blockers = meta.get("quality_blockers") or []
if quality_blockers:
    print(f"- quality_blockers: {', '.join(str(item) for item in quality_blockers)}")
retry_stages = meta.get("retry_stages") or []
if retry_stages:
    print(f"- retry_stages: {', '.join(str(item) for item in retry_stages)}")
print(f"- repair_attempts: {meta.get('repair_attempts', 0)}")
repair_models = meta.get("repair_models") or []
if repair_models:
    print(f"- repair_models: {', '.join(str(item) for item in repair_models)}")
print(f"- last_status_message: {meta.get('last_status_message', '')}")
artifacts = meta.get("artifacts", {})
if isinstance(artifacts, dict):
    draft_path = artifacts.get("repair_latest") or artifacts.get("draft_v2")
    if draft_path:
        print(f"- draft_path: {draft_path}")
    for label, key in (
        ("draft_v2", "draft_v2"),
        ("critique_v1", "critique_v1"),
        ("repair_latest", "repair_latest"),
        ("gate_v1", "gate_v1"),
        ("manuscript", "manuscript"),
        ("memory_summary", "memory_summary"),
    ):
        value = artifacts.get(key)
        if value:
            print(f"- {label}: {value}")
print(f"- meta: {meta_path}")
PY
}

export ANE_SMOKE_ROOT="${workspace}"
export ANE_SMOKE_CHAPTER="${chapter}"
export ANE_SMOKE_INTENTION="${intention}"

cd "${REPO_DIR}"
prepare_workspace

if [[ "${ANE_MODEL}" == apple-coreml:* ]]; then
  echo "Warm-up Apple runtime via ${ANE_BASE_URL} ..."
  warmup_openai_compatible
fi

decision_flag="--approve"
if [[ "${decision}" == "reject" ]]; then
  decision_flag="--reject"
fi

set +e
cli_output="$(
  cd "${workspace}" && \
  PYTHONPATH="${REPO_DIR}${PYTHONPATH:+:${PYTHONPATH}}" \
  python3 -m cli.main generate chapter --chapter "${chapter}" "${decision_flag}" 2>&1
)"
cli_exit=$?
set -e

printf '%s\n' "${cli_output}"
print_summary

if [[ ${cli_exit} -ne 0 ]]; then
  exit "${cli_exit}"
fi
