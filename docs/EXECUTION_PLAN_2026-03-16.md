# Plan d'execution - 16 mars 2026

Plan de reprise reel base sur l'etat code + runtime constate le 16 mars 2026.

References:

- contexte: [`CONTEXTE_PROJET_2026-03-16.md`](./CONTEXTE_PROJET_2026-03-16.md)
- memoire: [`MEMOIRE_REPRISE_2026-03-16.md`](./MEMOIRE_REPRISE_2026-03-16.md)
- spec systeme: [`SYSTEM_SPEC_2026-03-16.md`](./SYSTEM_SPEC_2026-03-16.md)
- carte agents: [`AGENTS_2026-03-16.md`](./AGENTS_2026-03-16.md)
- backlog actif: [`../TODO_ACTIVE.md`](../TODO_ACTIVE.md)

## Lot 1 - Restaurer le control plane local [LIVRE]

- `:8100` mascarade UP (`apple-coreml` + `ollama`)
- `:8201` Apple LLM UP — `qwen3.5-4b-onnx-q4f16` actif
- `:8091` llama-server UP — `ollama:qwen2.5:7b` actif

## Lot 2 - Requalifier le chemin `llama.cpp` [LIVRE]

- `llama-server` expose `ollama:qwen2.5:7b` sur `:8091`
- preflight ANE OpenAI-compatible passe
- lot `priority_models` lance avec qwen2.5:7b en cours

## Lot 3 - Rejoyer les lots utiles [EN COURS]

### Ordre

1. `baselines` — TERMINE (rapport `20260316T195716Z`)
2. `priority_models` — EN COURS (rapport `20260316T204232Z`)
3. `french_models` — A FAIRE (mistral-nemo via `:8091`)
4. `tracking_sync` — apres french_models

### Done quand

- `ollama:qwen2.5:7b` et `ollama:qwen2.5:1.5b` ne sont plus `provider_failed` par defaut
- `ollama:mistral-nemo:latest` a un verdict qualite (pas runtime)

## Lot 4 - Revenir aux blockers narratifs

### Objectif

- reprendre `rewrite` / `repair` une fois le runtime stabilise, sous les nouveaux prompts

### Livres (lot refonte 16 mars — phases 1 a 5)

- prompts `draft_v1`, `rewrite_v1`, `repair_v1` reinforces : output primer + few-shot BAD/GOOD + cible 600-800 mots
- 4 bare `except Exception` corriges dans `core/next_lots.py`
- tests `IntentionGate`, `PromptStore`, CLI intention : suite a 111 tests verts
- `_normalize_generated_prose()` : strip ALL `#{1,6}` headings avant gate
- `_is_outline_like()` : fix false positive "scene", ajout `dense_bullet_list` (4+ bullets)
- `_close_json_delimiters()` : rebuild car-par-car, mismatched + stray closers
- `_finish_stage()` extrait, `_iter_chapters_with_status()` extrait
- fix `outline_like` valide sur baselines : `qwen2.5:1.5b` → `quality_blocked ['truncated_ending']` seulement

### Cibles restantes

- valider `qwen2.5:7b` sous prompts nouveaux via lot `priority_models` en cours
- verifier `ollama:mistral-nemo:latest` via lot `french_models` a faire
- `truncated_ending` persistant sur `qwen2.5-0.5b` et `qwen2.5:1.5b` — modeles trop petits, attendu

### A moyen terme

- evaluer `prometheus-eval` ou `story-evaluation-llm` comme remplacement gate heuristique
- regarder `dottxt/outlines` si grammar sampling disponible via llama-server

## Lot 5 - Consolider l'exploitation

### Objectif

- garder une boucle d'observabilite legere et fiable

### Done quand

- `scripts/ops_tui.py` devient le point d'entree court terme pour lire projet + lots + logs
- `docs/runbooks/AUTOMATION.md` couvre l'usage TUI, l'analyse des logs et la purge dry-run

## Lot 6 - Robustesse reprise (nouveau)

### Objectif

- rendre les ecritures d'etat resilientes aux interruptions
- eviter qu'un JSON partiellement ecrit bloque la reprise

### Livres (17 mars)

- ecritures JSON atomiques dans `core/generation/pipeline.py` et `core/next_lots.py`
- lectures metadata/index tolerantes aux JSON corrompus dans `pipeline` et `loader`
- runbook de recovery ajoute: `docs/runbooks/RECOVERY_PROCEDURES.md`
- suite unitaire: 111 tests verts

### Cibles restantes

- ajouter des tests de corruption JSON dedies (meta chapitre + state automation)
- ajouter une commande de verification JSON en preflight ops

## Lot 7 - Mascarade multi-host (tower/kxkm)

### Objectif

- operer ANE sur deux cibles SSH avec un cockpit unique
- garder un mode TUI-first pour supervision et relance

### Livres (17 mars)

- `automation/mascarade_hosts.toml` ajoute (tower + kxkm)
- `scripts/mascarade_remote_tui.py` ajoute (probe SSH + sante tunnel)
- `scripts/setup_mascarade_launchd.py` ajoute (render/install/uninstall/status)
- plists de reference ajoutes sous `automation/launchd/`
- test unitaire ajoute: `tests/test_setup_mascarade_launchd.py`
- README + runbook automation synchronises

### Cibles restantes

- valider les deux sessions tunnel en conditions reelles
- activer launchd en reel et verifier `status`
- fallback autossh si l'environnement reseau rend launchd insuffisant

### Etat rerun qualite (17 mars)

- rerun `priority_models` relance, stoppe sur checkpoint runtime Apple (`aucun modele` expose au lieu de `qwen3.5-4b-onnx-q4f16`)
- prochaine action immediate: `prepare_runtime_step.sh` puis reprise `--resume`

## Lot 8 - Refonte runtime ANE (phase 1) [EN COURS]

### Objectif

- sortir les concepts runtime hors du pipeline narratif
- garder `core/generation/provider.py` comme facade de compatibilite pendant la migration

### Livres (21 mars)

- package `core/runtime/` explicite dans le repo
- contraintes runtime explicites (`json-best-effort`, switch Apple semi-manuel)
- healthcheck runtime capable de lire un catalogue de modeles OpenAI-compatible
- tests dedies runtime ajoutes

### Cibles restantes

- faire consommer `core/runtime/*` par `core/next_lots.py`
- brancher `scripts/ops_tui.py` et les preflights sur une sonde runtime unique
- introduire des profils runtime nommes (local, remote, `llama.cpp`, Apple)

## Risque a eviter

Ne pas retourner dans une boucle de tuning prompts avant d'avoir remonte `:8100` et valide `qwen2.5:7b` sur le chemin `llama.cpp`.

## Auto-sync
<!-- AUTO-SYNC:ANE-PLAN:START -->
- dernier verdict automatise: 2026-03-17T09:44:06+00:00
- accepted: apple-coreml:qwen3.5-4b-onnx-q4f16
- gate atteint: apple-coreml:qwen3.5-4b-onnx-q4f16, ollama:qwen2.5:7b, apple-coreml:qwen2.5-0.5b-instruct-onnx, ollama:qwen2.5:1.5b, ollama:mistral-nemo:latest
- prochain lot calcule: Reference locale reconfirmee; resserrer rewrite/repair sur les modeles deja bloques a gate.
- checkpoint manuel requis: Le runtime Apple sert `aucun modèle` au lieu de `qwen3.5-4b-onnx-q4f16`.
<!-- AUTO-SYNC:ANE-PLAN:END -->
