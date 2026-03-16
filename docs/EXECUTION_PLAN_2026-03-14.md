# Plan d'execution - 14 mars 2026

Plan de reprise base sur l'etat reel du 14 mars 2026.

References:

- contexte: [`CONTEXTE_PROJET_2026-03-14.md`](./CONTEXTE_PROJET_2026-03-14.md)
- memoire: [`MEMOIRE_REPRISE_2026-03-14.md`](./MEMOIRE_REPRISE_2026-03-14.md)
- backlog actif: [`../TODO_ACTIVE.md`](../TODO_ACTIVE.md)
- comparatif courant: [`MODEL_COMPARISON_2026-03-08.md`](./MODEL_COMPARISON_2026-03-08.md)

## Lot 1 - Industrialiser le contournement `llama.cpp`

### Etat constate

- `ollama:qwen2.5:7b` et `ollama:qwen2.5:1.5b` echouent encore en runtime natif
- `llama-server` sait deja charger un blob Ollama local et repondre vite
- le blob `qwen2.5:1.5b` a deja repondu via `llama-server`

### Objectif

- disposer d'un chemin local stable pour les modeles `qwen2.5` sans dependre du runtime Ollama natif

### Done quand

- un backend `llama.cpp` est branchable de facon reproductible pour `qwen2.5:1.5b`
- le routage `provider:model` reste pilotable depuis `mascarade`

## Lot 2 - Etendre au 7B

### Etat constate

- le 7B reste le meilleur candidat alternatif cote qualite
- son blocage courant est d'abord runtime, pas prompt

### Objectif

- verifier si le meme chemin `llama.cpp` peut servir `qwen2.5:7b`

### Done quand

- un preflight et un smoke simple du 7B passent via le backend alternatif

## Lot 3 - Rejouer les lots utiles

### Objectif

- rerun `priority_models` puis `baselines` sur un runtime local stable

### Done quand

- les deux modeles `qwen2.5` ne sont plus `provider_failed`
- le comparatif reflete enfin des verdicts qualite plutot que des erreurs de runtime

## Lot 4 - Revenir aux vrais blockers qualite

### Objectif

- reprendre `rewrite` / `repair` seulement sur les blockers qui subsistent apres stabilisation runtime

### Cible

- `outline_like` pour le meilleur candidat alternatif
- `truncated_ending` pour la baseline Apple encore bloquee

## Risque a eviter

Ne pas re-rentrer dans une boucle de tuning prompts tant que les reruns `qwen2.5` passent par un runtime non fiable.

## Auto-sync
<!-- AUTO-SYNC:ANE-PLAN:START -->
- dernier verdict automatise: 2026-03-14T14:03:06+00:00
- accepted: apple-coreml:qwen3.5-4b-onnx-q4f16
- gate atteint: apple-coreml:qwen3.5-4b-onnx-q4f16, apple-coreml:qwen2.5-0.5b-instruct-onnx
- prochain lot calcule: Reference locale reconfirmee; retablir le runtime des modeles provider_failed puis reprendre rewrite/repair sur les modeles bloques a gate.
<!-- AUTO-SYNC:ANE-PLAN:END -->
