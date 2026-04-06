# Repository Guidelines

## Project Structure & Module Organization
The root repository is the Python narrative engine. Use `cli/` for the public CLI, `core/` for pipeline, runtime, reporting, and project logic, and `scripts/` for smoke tests, TUIs, and automation entrypoints. Unit tests live in `tests/`. Prompt templates are versioned in `prompts/`. Automation state, reports, and manifests live under `automation/`. Long-form documentation and runbooks live in `docs/` and `docs/runbooks/`. The macOS Studio app is a separate Swift package in `app_AI-novel-engine/` with its own `Sources/` and `Tests/`.

## Build, Test, and Development Commands
Run the main Python suite with `make test` or `python3 -m unittest discover -s tests -v`. Use `make healthcheck` before runtime-dependent work to verify local services on `:8100`, `:8201`, `:8091`, and `:11434`. Launch a representative generation smoke test with `bash scripts/smoke_local_generation.sh --base-url http://127.0.0.1:8100 --model "apple-coreml:qwen3.5-4b-onnx-q4f16" --approve`. Drive automation with `python3 scripts/run_next_lots.py --lot full` or `make lot-full`. For the Studio app, run `DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swift test` inside `app_AI-novel-engine/`.

## Coding Style & Naming Conventions
Follow existing style rather than introducing a new formatter. Python uses 4-space indentation, type hints, dataclasses where appropriate, `snake_case` for functions/modules, and `PascalCase` for classes. Keep CLI and runtime constants explicit and environment-variable names uppercase, for example `ANE_BASE_URL`. Swift code in `app_AI-novel-engine/` follows standard Swift naming: `PascalCase` types, `camelCase` members.

## Testing Guidelines
Add Python tests in `tests/test_*.py` and group cases in `unittest.TestCase` classes named `*Tests`. Prefer deterministic unit tests with mocks over live runtime calls. When touching automation or tracking, cover both file outputs and state transitions. If you change the Swift app, add or update SwiftPM tests in `app_AI-novel-engine/Tests/`.

## Commit & Pull Request Guidelines
Recent history favors concise Conventional Commit subjects such as `feat(pipeline): ...`, `fix(lots): ...`, and `chore(gen): ...`. Keep commits scoped to one concern. PRs should explain the affected workflow, list verification commands, link any relevant issue or dated doc, and include screenshots when `app_AI-novel-engine/` UI changes.

## Configuration & Generated Content
Do not commit secrets. Local runtime setup relies on `ANE_PROVIDER`, `ANE_BASE_URL`, `ANE_MODEL`, `ANE_API_KEY`, and optional `OPENAI_API_KEY`. Do not hand-edit sections wrapped in `AUTO-SYNC` markers; regenerate them through the supported scripts.
