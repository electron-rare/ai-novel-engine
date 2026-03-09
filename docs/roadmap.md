# Roadmap v2

Roadmap courte et concrete, alignee sur l'etat reel du repo.

## Priorite 1 - Passer au moins un modele jusqu'a `gate`

- compacter `rewrite` pour qu'au moins un modele atteigne `gate`
- conserver la boucle `repair` et le garde-fou comme blocages durs
- viser d'abord `apple-coreml:qwen3.5-4b-onnx-q4f16` et `ollama:qwen2.5:7b`

## Priorite 2 - Requalifier les modeles plus lourds

- garder `apple-coreml:qwen2.5-0.5b-instruct-onnx` et `ollama:qwen2.5:1.5b` comme baselines vitesse
- rejouer `qwen3.5:9b` seulement si `qwen2.5:7b` termine un smoke complet
- maintenir les modeles toujours explicites dans les smokes et la doc
- tenir compte du fait que le runtime Apple local ne sert qu'un `model_id` a la fois

## Priorite 3 - Exploitation locale et docs

- runbook local ANE centre sur `rewrite`, `gate_v1.json`, `repair_vN.md` et `quality_blocked`
- runbook Apple local cote `mascarade` aligne sur les statuts reels
- README et suivi croises pointent vers `EXECUTION_PLAN_2026-03-08.md`

## Source de verite

- backlog actif: [`../TODO_ACTIVE.md`](../TODO_ACTIVE.md)
- etat livre: [`../TODO_IMPLEMENTE.md`](../TODO_IMPLEMENTE.md)
- ordre d'execution: [`EXECUTION_PLAN_2026-03-08.md`](./EXECUTION_PLAN_2026-03-08.md)
