# AI Novel Engine — Makefile

# ── Tests ──────────────────────────────────────────────────────────────────
test:
	python3 -m unittest discover -s tests -q

test-v:
	python3 -m unittest discover -s tests -v

# ── TUI / Supervision ──────────────────────────────────────────────────────
tui:
	python3 scripts/next_lots_tui.py --watch --interval 2

ops-tui:
	python3 scripts/ops_tui.py --watch --interval 3

# ── Reports ────────────────────────────────────────────────────────────────
reports-summary:
	python3 scripts/reports_ops.py summary

reports-errors:
	python3 scripts/reports_ops.py analyze-logs --top 15

reports-prune-dry:
	python3 scripts/reports_ops.py prune --days 14

reports-prune:
	python3 scripts/reports_ops.py prune --days 14 --delete-workspaces --apply

# ── Healthcheck services locaux ────────────────────────────────────────────
healthcheck:
	@echo "==> Services locaux"
	@curl -sf http://127.0.0.1:8100/health && echo "  :8100 mascarade  OK" || echo "  :8100 mascarade  DOWN"
	@curl -sf http://127.0.0.1:8201/health && echo "  :8201 apple      OK" || echo "  :8201 apple      DOWN"
	@curl -sf http://127.0.0.1:8091/health && echo "  :8091 llama-srv  OK" || echo "  :8091 llama-srv  DOWN"
	@curl -sf http://127.0.0.1:11434/api/tags > /dev/null && echo "  :11434 ollama    OK" || echo "  :11434 ollama    DOWN"

# ── Smoke chapter ──────────────────────────────────────────────────────────
smoke-apple:
	bash scripts/smoke_local_generation.sh \
	  --base-url http://127.0.0.1:8100 \
	  --model "apple-coreml:qwen3.5-4b-onnx-q4f16" \
	  --approve

smoke-ollama:
	bash scripts/smoke_local_generation.sh \
	  --base-url http://127.0.0.1:8091 \
	  --model "ollama:qwen2.5:7b" \
	  --approve

smoke-mistral:
	bash scripts/smoke_local_generation.sh \
	  --base-url http://127.0.0.1:8091 \
	  --model "ollama:mistral-nemo:latest" \
	  --approve

# ── Lots automation ────────────────────────────────────────────────────────
lot-priority:
	python3 scripts/run_next_lots.py --lot priority_models

lot-baselines:
	python3 scripts/run_next_lots.py --lot baselines

lot-french:
	python3 scripts/run_next_lots.py --lot french_models

lot-full:
	python3 scripts/run_next_lots.py --lot full

lot-sync:
	python3 scripts/run_next_lots.py --lot tracking_sync --report-only

resume:
	python3 scripts/run_next_lots.py --resume automation/state/next_lots_state.json

# ── Git ────────────────────────────────────────────────────────────────────
status:
	git status
