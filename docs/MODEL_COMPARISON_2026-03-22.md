# Comparatif local ANE - 22 mars 2026

Comparatif court apres reruns cibles avec juge narratif secondaire.

## Lecture rapide

- `apple-coreml:qwen3.5-4b-onnx-q4f16` reste la seule reference `accepted`
- `ollama:qwen2.5:7b` devient le premier chemin Ollama local `accepted`
- `ollama:mistral-nemo:latest` n'a plus de faux `outline_like`, mais ne suit pas la meme retouche de fin de scene

## Resultats utiles

| Modele | Backend cible | Verdict 22 mars | Blockers finaux | Lecture operative |
|---|---|---|---|---|
| `apple-coreml:qwen3.5-4b-onnx-q4f16` | `apple-coreml` | `accepted` (historique de reference) | — | reference locale actuelle |
| `ollama:qwen2.5:7b` | `llama.cpp` / `llama-server` | `accepted` sur rerun consequencefix | — | premiere baseline Ollama locale promue; la contrainte "meme lieu, meme minute" ferme correctement la scene |
| `ollama:qwen2.5:1.5b` | `llama.cpp` / `llama-server` | `quality_blocked` (historique) | `truncated_ending` | petit modele encore utile comme baseline technique |
| `ollama:mistral-nemo:latest` | `llama.cpp` / `llama-server` | `quality_blocked` | `truncated_ending` sur rerun budgete; `outline_like`, `missing_immediate_consequence` sur rerun prompté; `missing_immediate_consequence` sur rerun gatefix; `truncated_ending`, `missing_risky_decision`, `missing_immediate_consequence` sur rerun consequencefix | le budget aide et le gate corrige supprime le faux positif de forme, mais la retouche commune de fin de scene degrade ce modele |

## Implication

Le prochain lot ne doit pas rouvrir le runtime. Il doit :

- garder `qwen2.5:7b` comme reference Ollama locale `accepted`
- ouvrir un chantier prompt/repair specifique a `mistral-nemo`; la retouche commune n'est plus une hypothese tenable

## Auto-sync
<!-- AUTO-SYNC:ANE-COMPARISON:START -->
- dernier cycle automatise: 2026-03-23T21:34:05+00:00

| Modele | Categorie | Preflight | Smoke | Classification | Failed stage | Gate | Repairs | Notes |
|---|---|---|---|---|---|---|---:|---|
| ollama:qwen2.5:7b | priority_models | KO | non | provider_failed |  | non | 0 | Le preflight OpenAI-compatible a échoué. |
| apple-coreml:qwen2.5-0.5b-instruct-onnx | runtime_preflight | n/a | non | dry_run |  | non | 0 | Dry-run: aucun preflight ni smoke exécuté. |
| apple-coreml:qwen3.5-4b-onnx-q4f16 | runtime_preflight | n/a | non | dry_run |  | non | 0 | Dry-run: aucun preflight ni smoke exécuté. |
| ollama:qwen2.5:1.5b | runtime_preflight | n/a | non | dry_run |  | non | 0 | Dry-run: aucun preflight ni smoke exécuté. |
| mistral:mistral-large-latest | french_models | OK | oui | accepted |  | oui | 0 |  |
| ollama:mistral-nemo:latest | french_models | KO | non | provider_failed |  | non | 0 | Le preflight OpenAI-compatible a échoué. |
<!-- AUTO-SYNC:ANE-COMPARISON:END -->
