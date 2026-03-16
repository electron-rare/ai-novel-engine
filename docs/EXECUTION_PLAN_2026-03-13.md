# Plan d'execution - 13 mars 2026

Plan de reprise apres revue des rapports du 9 mars 2026 et remise a plat du suivi.

References:

- memoire de reprise: [`MEMOIRE_REPRISE_2026-03-13.md`](./MEMOIRE_REPRISE_2026-03-13.md)
- backlog actif: [`../TODO_ACTIVE.md`](../TODO_ACTIVE.md)
- lots livres: [`../TODO_IMPLEMENTE.md`](../TODO_IMPLEMENTE.md)
- comparatif courant: [`MODEL_COMPARISON_2026-03-08.md`](./MODEL_COMPARISON_2026-03-08.md)

Pilotage:

- lancer un cycle complet: `python3 scripts/run_next_lots.py --lot full`
- resynchroniser seulement les docs: `python3 scripts/run_next_lots.py --lot tracking_sync --report-only`

## Lot 1 - Garder le chemin critique ferme et rerunnable

### Etat constate

- le `state` courant est clos et synchronise
- `stateful-mistral7b-instruct-int4-coreml` est retire du lot critique
- le runtime minimal est revenu: `:8100`, `:8201` et `:11434/api/tags` repondent
- `mascarade-core` et `mascarade-api` ont ete recrees avec le bon `OLLAMA_BASE_URL`
- le blocage live restant est maintenant plus precis: `ollama` natif 0.17.7 plante en generation sur `qwen2.5:7b` et `qwen2.5:1.5b` a cause du backend Metal

### Objectif

- garder `full` focalise sur les modeles utiles
- garder Apple et le core en etat, puis rebrancher un chemin Ollama CPU avant les vrais reruns qualite

### Done quand

- `automation/state/next_lots_state.json` reste sans checkpoint ambigu
- les endpoints Apple et core repondent de nouveau
- un chemin Ollama CPU redevient executable pour les smokes comparatifs

### Risque principal

- un runtime partiellement revenu peut masquer un blocage plus fin du backend Ollama si on s'arrete au simple `api/tags`

## Lot 2 - Corriger les epreuves qualite, pas ajouter de complexite

### Etat constate

- `ollama:qwen2.5:7b` atteint `gate` mais reste bloque sur `outline_like`
- `apple-coreml:qwen2.5-0.5b-instruct-onnx` et `ollama:qwen2.5:1.5b` finissent sur `truncated_ending`
- la reference Apple 4B a deja prouve qu'un cycle `accepted` est possible
- le rerun comparable `automation/reports/apple_rerun_7oY51o` n'a pas reconfirme cette reference: `gate` bloque sur `too_short` + `truncated_ending`, puis `repair` echoue a cause de l'ancien fallback pipeline vers Ollama en `HTTP 502`
- le rerun comparable `automation/reports/apple_rerun_preset_20260313T223555Z` a depuis fini `accepted` sans `repair`; la reference Apple locale est reconfirmee

### Objectif

- resserrer `rewrite_v1`, `memory_v1` si besoin, et surtout la boucle `repair` sur les deux blocages reels:
  - prose trop proche d'un plan
  - fin de texte tronquee ou suspendue

### Done quand

- `ollama:qwen2.5:7b` finit au moins une fois `accepted`
- au moins une baseline sort de `truncated_ending` ou est officiellement releguee a simple test de regression

### Risque principal

- augmenter les budgets sans clarifier les consignes risque d'allonger les runs sans faire tomber les blockers

## Lot 3 - Reference locale reconfirmee

### Etat constate

- `apple-coreml:qwen3.5-4b-onnx-q4f16` a maintenant deux runs comparables `accepted`
- le rerun `automation/reports/apple_rerun_preset_20260313T223555Z` est passe de bout en bout avec `repair_attempts=0`

### Objectif

- figer la reference Apple locale et sortir ce sujet du flux d'incertitude; les reruns Apple restent maintenant isoles d'un fallback Ollama par defaut

### Done quand

- deux runs comparables au meme preset passent jusqu'a `accepted`
- la doc peut nommer une reference locale sans ambiguite

### Risque principal

- laisser la doc ou le suivi parler d'une reference "a confirmer" alors que le point est deja tranche

## Lot 4 - Garder une memoire projet exploitable

### Objectif

- faire en sorte que README, TODO, plan et runbook racontent la meme chose
- ne plus perdre les bons resultats lorsqu'un lot partiel plus recent tourne apres un lot complet

### Done quand

- `tracking_sync` consolide les derniers verdicts connus par modele
- les documents de suivi renvoient tous vers ce plan du 13 mars 2026

### Risque principal

- si les docs versionnees ne pointent pas vers le bon plan, la reprise devient plus couteuse que le code

## Auto-sync
<!-- AUTO-SYNC:ANE-PLAN:START -->
- dernier verdict automatise: 2026-03-14T10:06:55+00:00
- accepted: apple-coreml:qwen3.5-4b-onnx-q4f16
- gate atteint: apple-coreml:qwen3.5-4b-onnx-q4f16, apple-coreml:qwen2.5-0.5b-instruct-onnx
- prochain lot calcule: Reference locale reconfirmee; retablir le runtime des modeles provider_failed puis reprendre rewrite/repair sur les modeles bloques a gate.
<!-- AUTO-SYNC:ANE-PLAN:END -->
