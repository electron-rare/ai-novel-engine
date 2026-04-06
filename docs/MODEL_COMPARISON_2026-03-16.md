# Comparatif local ANE - 16 mars 2026

Comparatif de reprise aligne sur le protocole courant et sur les faits confirmes les plus utiles.

## Lecture rapide

- `apple-coreml:qwen3.5-4b-onnx-q4f16` reste la reference `accepted`
- `apple-coreml:qwen2.5-0.5b-instruct-onnx` reste une baseline `quality_blocked`
- `ollama:qwen2.5:1.5b` a deux lectures utiles:
  - dernier etat automatise historise: `provider_failed`
  - preuve de reprise manuelle via `llama-server`: `quality_blocked` a `gate`
- `ollama:qwen2.5:7b` reste le meilleur candidat alternatif, mais sa requalification via `llama.cpp` reste a faire sur un rerun comparable recent

## Resultats utiles (mis a jour 16 mars 2026 session 2)

| Modele | Backend cible | Verdict 16 mars session 2 | Blocker principal | Lecture operative |
|---|---|---|---|---|
| `apple-coreml:qwen3.5-4b-onnx-q4f16` | `apple-coreml` | `accepted` (reconfirme) | — | reference locale actuelle; rerun avec budgets 1024 confirme |
| `apple-coreml:qwen2.5-0.5b-instruct-onnx` | `apple-coreml` | `quality_blocked` | `truncated_ending` | fix `dense_bullet_list` catch listes pures en repair |
| `ollama:qwen2.5:7b` | `llama.cpp` / `llama-server` | `quality_blocked` | `truncated_ending` (LLM gate) | prose coherente mais fin narrative insuffisante pour gate LLM |
| `ollama:qwen2.5:1.5b` | `llama.cpp` / `llama-server` | `quality_blocked` | `truncated_ending` | plus d'`outline_like` (fix normalisation); manque de longueur |
| `ollama:mistral-nemo:latest` | `llama.cpp` / `llama-server` | en cours | — | lot french_models en cours (rapport 20260316T220423Z) |

## Implication

Le comparatif utile n'oppose plus "Apple vs Ollama" mais "prose complete vs incomplete" :

- reference Apple `qwen3.5-4b` : `accepted` stable avec budgets 1024
- `qwen2.5:7b` : runtime stable, blocker narratif — gate LLM stricter que heuristique sur fin de scene
- `qwen2.5:1.5b` : fix `outline_like` valide; reste `truncated_ending` (modele trop petit)
- mistral-nemo : premier run francophone, verdict en cours

## Auto-sync
<!-- AUTO-SYNC:ANE-COMPARISON:START -->
- dernier cycle automatise: 2026-03-17T09:44:06+00:00

| Modele | Categorie | Preflight | Smoke | Classification | Failed stage | Gate | Repairs | Notes |
|---|---|---|---|---|---|---|---:|---|
| apple-coreml:qwen3.5-4b-onnx-q4f16 | priority_models | OK | oui | accepted |  | oui | 0 |  |
| ollama:qwen2.5:7b | priority_models | OK | oui | quality_blocked | gate | oui | 2 |  |
| apple-coreml:qwen2.5-0.5b-instruct-onnx | baselines | OK | oui | quality_blocked | gate | oui | 2 |  |
| ollama:qwen2.5:1.5b | baselines | OK | oui | quality_blocked | gate | oui | 2 |  |
| ollama:mistral-nemo:latest | french_models | OK | oui | quality_blocked | gate | oui | 2 |  |
<!-- AUTO-SYNC:ANE-COMPARISON:END -->
