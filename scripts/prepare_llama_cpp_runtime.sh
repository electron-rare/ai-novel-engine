#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

MODEL=""
HOST="127.0.0.1"
PORT="8091"
CTX_SIZE="${LLAMA_CPP_CTX_SIZE:-8192}"
GPU_LAYERS="${LLAMA_CPP_GPU_LAYERS:-999}"
THREADS="${LLAMA_CPP_THREADS:-}"
ALIASES=""
LOG_FILE=""
RESUME_STATE=""
ANE_SCRIPT=""

usage() {
  cat <<'EOF'
Usage: scripts/prepare_llama_cpp_runtime.sh [options]

Prepare the manual command needed to serve an Ollama model through llama-server
with an OpenAI-compatible alias usable by ai-novel-engine.

Options:
  --model <name>         Ollama model name, with or without the `ollama:` prefix
  --host <host>          Host to bind llama-server on (default: 127.0.0.1)
  --port <port>          Port to bind llama-server on (default: 8091)
  --ctx-size <tokens>    Context size to pass to llama-server (default: 8192)
  --gpu-layers <n>       GPU layers setting for llama-server (default: 999)
  --threads <n>          CPU threads for llama-server (default: unset)
  --aliases <csv>        Extra aliases to expose in addition to the ANE defaults
  --log-file <path>      Log file path for llama-server
  --resume-state <path>  State file to resume in ai-novel-engine
  --ane-script <path>    Path to ai-novel-engine/scripts/run_next_lots.py
  -h, --help             Show this help
EOF
}

die() {
  echo "$*" >&2
  exit 2
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"
}

normalize_model_name() {
  local raw="$1"
  if [[ "$raw" == ollama:* ]]; then
    printf '%s\n' "${raw#ollama:}"
    return
  fi
  printf '%s\n' "$raw"
}

slugify() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9' '_'
}

join_aliases() {
  local raw_model="$1"
  local extra_aliases="$2"
  local joined="ollama:${raw_model},${raw_model}"
  if [[ -n "$extra_aliases" ]]; then
    joined="${joined},${extra_aliases}"
  fi
  printf '%s\n' "$joined"
}

resolve_blob_path() {
  local raw_model="$1"
  local modelfile
  local from_line

  modelfile="$(ollama show --modelfile "$raw_model" 2>/dev/null || true)"
  from_line="$(printf '%s\n' "$modelfile" | awk '/^FROM / { print substr($0, 6); exit }')"

  [[ -n "$from_line" ]] || die "Unable to resolve a GGUF blob for Ollama model: ${raw_model}"
  [[ -e "$from_line" ]] || die "Resolved GGUF blob does not exist: ${from_line}"
  printf '%s\n' "$from_line"
}

print_resume_hint() {
  if [[ -n "${RESUME_STATE}" && -n "${ANE_SCRIPT}" ]]; then
    printf '\n# resume ANE lot\npython3 %q --resume %q\n' "${ANE_SCRIPT}" "${RESUME_STATE}"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)
      MODEL="${2:-}"
      shift 2
      ;;
    --host)
      HOST="${2:-}"
      shift 2
      ;;
    --port)
      PORT="${2:-}"
      shift 2
      ;;
    --ctx-size)
      CTX_SIZE="${2:-}"
      shift 2
      ;;
    --gpu-layers)
      GPU_LAYERS="${2:-}"
      shift 2
      ;;
    --threads)
      THREADS="${2:-}"
      shift 2
      ;;
    --aliases)
      ALIASES="${2:-}"
      shift 2
      ;;
    --log-file)
      LOG_FILE="${2:-}"
      shift 2
      ;;
    --resume-state)
      RESUME_STATE="${2:-}"
      shift 2
      ;;
    --ane-script)
      ANE_SCRIPT="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "Unknown argument: $1"
      ;;
  esac
done

[[ -n "$MODEL" ]] || die "--model is required"
[[ -n "$HOST" ]] || die "--host cannot be empty"
[[ "$PORT" =~ ^[0-9]+$ ]] || die "--port must be an integer"
[[ "$CTX_SIZE" =~ ^[0-9]+$ ]] || die "--ctx-size must be an integer"
[[ "$GPU_LAYERS" =~ ^-?[0-9]+$ ]] || die "--gpu-layers must be an integer"
if [[ -n "$THREADS" && ! "$THREADS" =~ ^[0-9]+$ ]]; then
  die "--threads must be an integer"
fi

require_cmd ollama
require_cmd llama-server

RAW_MODEL="$(normalize_model_name "$MODEL")"
BLOB_PATH="$(resolve_blob_path "$RAW_MODEL")"
MODEL_ALIASES="$(join_aliases "$RAW_MODEL" "$ALIASES")"

if [[ -z "$LOG_FILE" ]]; then
  LOG_FILE="${TMPDIR:-/tmp}/ane_llama_cpp_$(slugify "$RAW_MODEL").log"
fi

cat <<EOF
# start llama.cpp runtime for ${RAW_MODEL}
cd ${REPO_DIR}

# optional: inspect any existing listener before starting a new runtime
lsof -nP -iTCP:${PORT} -sTCP:LISTEN || true

nohup $(command -v llama-server) \\
  --model $(printf '%q' "${BLOB_PATH}") \\
  --alias $(printf '%q' "${MODEL_ALIASES}") \\
  --host $(printf '%q' "${HOST}") \\
  --port $(printf '%q' "${PORT}") \\
  --ctx-size $(printf '%q' "${CTX_SIZE}") \\
  --gpu-layers $(printf '%q' "${GPU_LAYERS}") \\
$(if [[ -n "$THREADS" ]]; then printf '  --threads %q \\\n' "${THREADS}"; fi)  > $(printf '%q' "${LOG_FILE}") 2>&1 &

sleep 2
curl -fsS http://${HOST}:${PORT}/health
curl -fsS http://${HOST}:${PORT}/v1/models
tail -n 40 $(printf '%q' "${LOG_FILE}") || true
EOF

print_resume_hint
