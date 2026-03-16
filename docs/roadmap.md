# Roadmap v2

Roadmap courte et concrete, alignee sur l'etat reel du repo au 13 mars 2026.

## Priorite 1 - Stabiliser la reprise

- garder `automation/state/next_lots_state.json` sans checkpoint ambigu
- garder `:8100` et `:8201` operationnels, puis retablir un vrai chemin Ollama CPU avant de rejouer `priority_models`
- garder `apple-coreml:qwen3.5-4b-onnx-q4f16` comme reference provisoire tant qu'un rerun comparable ne la contredit pas
- traiter le rerun `automation/reports/apple_rerun_7oY51o` comme une alerte de stabilite: la reference Apple n'est pas encore reconfirmee
- ne plus laisser les docs perdre un resultat `accepted` lorsqu'un lot partiel plus recent tourne ensuite

## Priorite 2 - Faire tomber les blockers reels

- sortir `ollama:qwen2.5:7b` de `outline_like`
- faire disparaitre `truncated_ending` sur au moins une baseline
- limiter les changements a `rewrite`, `repair` et leurs budgets tant qu'aucun autre blocker n'apparait

## Priorite 3 - Resserer la matrice locale

- garder `apple-coreml:qwen2.5-0.5b-instruct-onnx` et `ollama:qwen2.5:1.5b` comme baselines vitesse ou regression
- garder `stateful-mistral7b-instruct-int4-coreml` hors chemin critique tant qu'un besoin produit n'impose pas son retour
- maintenir les modeles et le runtime Apple explicites dans chaque smoke et chaque doc

## Source de verite

- contexte courant: [`CONTEXTE_PROJET_2026-03-14.md`](./CONTEXTE_PROJET_2026-03-14.md)
- memoire de reprise: [`MEMOIRE_REPRISE_2026-03-14.md`](./MEMOIRE_REPRISE_2026-03-14.md)
- backlog actif: [`../TODO_ACTIVE.md`](../TODO_ACTIVE.md)
- etat livre: [`../TODO_IMPLEMENTE.md`](../TODO_IMPLEMENTE.md)
- ordre d'execution: [`EXECUTION_PLAN_2026-03-14.md`](./EXECUTION_PLAN_2026-03-14.md)
