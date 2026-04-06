#!/usr/bin/env bash
# Vérifie l'état des ports runtime ANE et guide vers les actions correctives.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
TOML="${REPO_DIR}/automation/next_lots.toml"

# --- lecture TOML robuste via Python/tomllib -------------------------------
_toml_get() {
  local key="$1"
  python3 - "$TOML" "$key" <<'PY'
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

path = Path(sys.argv[1])
key = sys.argv[2]

try:
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
except (OSError, tomllib.TOMLDecodeError):
    print("")
    raise SystemExit(0)

paths = payload.get("paths") if isinstance(payload, dict) else {}
if not isinstance(paths, dict):
    print("")
    raise SystemExit(0)

value = paths.get(key, "")
print(str(value).strip())
PY
}

CORE_URL="$(_toml_get core_base_url)"
APPLE_URL="$(_toml_get apple_runtime_url)"
OLLAMA_TAGS="$(_toml_get ollama_tags_url)"
OPENAI_URL="$(_toml_get ollama_openai_base_url)"
OLLAMA_RUNTIME="$(_toml_get ollama_runtime)"

CORE_URL="${CORE_URL:-http://127.0.0.1:8100}"
APPLE_URL="${APPLE_URL:-http://127.0.0.1:8201}"
OLLAMA_TAGS="${OLLAMA_TAGS:-http://127.0.0.1:11434/api/tags}"
OPENAI_URL="${OPENAI_URL:-http://127.0.0.1:8091}"
OLLAMA_RUNTIME="${OLLAMA_RUNTIME:-native}"

# --- probe -----------------------------------------------------------------
probe() {
  local url="$1"
  local code
  if code=$(curl -s --max-time 2 "$url" -o /dev/null -w "%{http_code}" 2>/dev/null); then
    echo "UP(${code})"
  else
    echo "DOWN"
  fi
}

# --- affichage -------------------------------------------------------------
echo "=== ANE Runtime Healthcheck ==="
echo ""

CORE_STATUS=$(probe "${CORE_URL%/}/health")
APPLE_STATUS=$(probe "${APPLE_URL%/}/health")
OLLAMA_STATUS=$(probe "$OLLAMA_TAGS")
OPENAI_STATUS=$(probe "${OPENAI_URL%/}/health")

printf "  core  (mascarade %-25s  %s\n" "${CORE_URL}):" "$CORE_STATUS"
printf "  apple (ANE runtime %-24s  %s\n" "${APPLE_URL}):" "$APPLE_STATUS"
printf "  ollama daemon %-30s  %s\n" "(${OLLAMA_TAGS}):" "$OLLAMA_STATUS"
printf "  openai-compat (llama-server) %-14s  %s\n" "(${OPENAI_URL}):" "$OPENAI_STATUS"
printf "  ollama_runtime setting: %s\n" "$OLLAMA_RUNTIME"
echo ""

# --- guidance corrective ---------------------------------------------------
PROBLEMS=0

if [[ "$CORE_STATUS" == "DOWN" ]]; then
  echo "[!] core (:$(echo "$CORE_URL" | grep -oE '[0-9]{4,5}$' || echo '8100')) DOWN"
  echo "    -> Démarrer Mascarade (core Python OpenAI-compatible)"
  echo "       cd /path/to/mascarade && python3 -m mascarade.server"
  echo ""
  PROBLEMS=$((PROBLEMS + 1))
fi

if [[ "$APPLE_STATUS" == "DOWN" ]]; then
  echo "[!] apple (:$(echo "$APPLE_URL" | grep -oE '[0-9]{4,5}$' || echo '8201')) DOWN"
  echo "    -> Démarrer l'Apple ANE server (voir scripts/smoke_local_generation.sh)"
  echo ""
  PROBLEMS=$((PROBLEMS + 1))
fi

if [[ "$OPENAI_STATUS" == "DOWN" && "$OLLAMA_RUNTIME" == "openai_compatible" ]]; then
  echo "[!] llama-server (:$(echo "$OPENAI_URL" | grep -oE '[0-9]{4,5}$' || echo '8091')) DOWN"
  echo "    ollama_runtime = openai_compatible → les lots ollama:* vont déclencher un checkpoint."
  echo ""
  echo "    Pour démarrer llama-server sur qwen2.5:7b :"
  echo "      bash scripts/prepare_llama_cpp_runtime.sh --model qwen2.5:7b --port 8091"
  echo ""
  echo "    Pour démarrer llama-server sur qwen2.5:1.5b :"
  echo "      bash scripts/prepare_llama_cpp_runtime.sh --model qwen2.5:1.5b --port 8091"
  echo ""
  PROBLEMS=$((PROBLEMS + 1))
fi

if [[ "$OLLAMA_STATUS" == "DOWN" ]]; then
  echo "[!] Ollama daemon (:11434) ne répond pas"
  echo "    -> ollama serve"
  echo ""
  PROBLEMS=$((PROBLEMS + 1))
fi

if [[ $PROBLEMS -eq 0 ]]; then
  echo "[ok] Tous les services configurés répondent."
fi

echo "---"
echo "Cockpit ops : python3 scripts/ops_tui.py"
echo "Relancer un lot : python3 scripts/run_next_lots.py --lot priority_models"
echo "Reprendre : python3 scripts/run_next_lots.py --resume automation/state/next_lots_state.json"
exit 0
