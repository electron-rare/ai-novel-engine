# TODO actif - AI Novel Engine

Backlog courant pour reprendre `ai-novel-engine` sans melanger le reste avec les lots deja livres.

References:

- contexte courant: [`docs/CONTEXTE_PROJET_2026-03-14.md`](./docs/CONTEXTE_PROJET_2026-03-14.md)
- memoire de reprise: [`docs/MEMOIRE_REPRISE_2026-03-14.md`](./docs/MEMOIRE_REPRISE_2026-03-14.md)
- plan courant: [`docs/EXECUTION_PLAN_2026-03-14.md`](./docs/EXECUTION_PLAN_2026-03-14.md)
- lots livres: [`TODO_IMPLEMENTE.md`](./TODO_IMPLEMENTE.md)

## Memoire de reprise

- reference locale reconfirmee: `apple-coreml:qwen3.5-4b-onnx-q4f16` sur `20260309T055457Z` puis `apple_rerun_preset_20260313T223555Z`
- meilleur candidat alternatif: `qwen2.5:7b`, mais il faut d'abord lui rendre un runtime stable
- baselines vitesse a ce jour:
  - `apple-coreml:qwen2.5-0.5b-instruct-onnx` -> `quality_blocked`
  - `ollama:qwen2.5:1.5b` -> `provider_failed`
- faits live du 14 mars:
  - Apple warm-up direct sur `:8100` en `2.76s`
  - requete prose Apple representative en `39.99s`
  - `llama-server` a charge le blob `qwen2.5:1.5b` et a repondu en `0.31s`
- etat automatise clos; `stateful-mistral7b-instruct-int4-coreml` est hors chemin critique
- le suivi `tracking_sync` consolide maintenant les derniers resultats connus par modele au lieu de n'utiliser qu'un lot partiel recent

## Actif

- [ ] P0 Industrialiser un chemin `llama.cpp` / `llama-server` reusable pour `qwen2.5:1.5b`
- [ ] P0 Tester le blob local `qwen2.5:7b` via le meme chemin alternatif
- [ ] P1 Rejouer `priority_models` puis `baselines` des que le backend alternatif est branche
- [ ] P1 Reprendre `rewrite` / `repair` uniquement sur les blockers qui survivent apres stabilisation runtime

## Bloque

- [ ] P0 `ollama` natif 0.17.7 sur macOS 26.3.1 / Apple M5 echoue encore en generation sur `qwen2.5:7b` et `qwen2.5:1.5b` avec une erreur Metal / `HTTP 500`
- [ ] P1 Le runtime Apple local ne sert qu'un seul `model_id` a la fois; tout switch Apple reste une action manuelle ou semi-auto
- [ ] P1 `mascarade` route aujourd'hui `ollama:*` vers `/api/chat`, alors que `llama-server` expose surtout `/v1/chat/completions`; un pont runtime ou provider reste a creer

## Prochain ordre

- [ ] P0 Choisir le mode d'integration `llama.cpp`: adapter provider Mascarade ou shim local
- [ ] P0 Valider `qwen2.5:1.5b` de bout en bout via ce nouveau chemin
- [ ] P1 Etendre le meme chemin a `qwen2.5:7b`
- [ ] P1 Relancer `python3 scripts/run_next_lots.py --lot priority_models`
- [ ] P1 Relancer ensuite `python3 scripts/run_next_lots.py --lot baselines`
- [ ] P1 Garder `automation/reports/apple_rerun_preset_20260313T223555Z` comme rerun de reference pour les comparaisons Apple futures

## Auto-sync
<!-- AUTO-SYNC:ANE-TODO-ACTIVE:START -->
- dernier cycle automatique: 2026-03-14T14:03:06+00:00
- modeles accepted: apple-coreml:qwen3.5-4b-onnx-q4f16
- modeles ayant atteint gate: apple-coreml:qwen3.5-4b-onnx-q4f16, apple-coreml:qwen2.5-0.5b-instruct-onnx
- quality_blocked: apple-coreml:qwen2.5-0.5b-instruct-onnx
- provider_failed: ollama:qwen2.5:7b, ollama:qwen2.5:1.5b
- prochain lot recommande: Reference locale reconfirmee; retablir le runtime des modeles provider_failed puis reprendre rewrite/repair sur les modeles bloques a gate.
<!-- AUTO-SYNC:ANE-TODO-ACTIVE:END -->
