# Plan d'execution - 8 mars 2026

Plan de reference apres livraison de la boucle `repair`.

Le plan du 7 mars 2026 reste archive pour historique. L'ordre recommande a date
est celui-ci.

Pilotage operationnel:
- lancer les lots avec `python3 scripts/run_next_lots.py --lot <lot>`
- utiliser `automation/next_lots.toml` comme source de verite pour l'ordre des smokes, les budgets et les fichiers de suivi
- en cas de switch Apple ou de restart runtime, reprendre ensuite avec `python3 scripts/run_next_lots.py --resume automation/state/next_lots_state.json`

## Lot 1 - Consolider la reference acceptee et finir les baselines

### Etat constate
- la boucle `repair` est livree, testee et visible dans `status` / `meta.json`
- `apple-coreml:qwen3.5-4b-onnx-q4f16` a termine un cycle complet et est `accepted`
- `ollama:qwen2.5:7b` atteint `gate`, exerce `repair` en live, puis reste `quality_blocked` sur `outline_like`
- le lot `baselines` est en cours pour `apple-coreml:qwen2.5-0.5b-instruct-onnx` et `ollama:qwen2.5:1.5b`
- le runtime Apple local n'expose qu'un seul `model_id` a la fois, ce qui limite le fallback `repair` entre modeles Apple au sein d'un meme smoke

### Objectif
- finir les baselines pour avoir un comparatif complet du protocole courant
- confirmer que la reference `apple-coreml:qwen3.5-4b-onnx-q4f16` est reproductible sur plus d'un cycle
- sortir `ollama:qwen2.5:7b` de `quality_blocked` sans degrader la prose utile

### Done quand
- le lot `baselines` est termine et synchronise
- `apple-coreml:qwen3.5-4b-onnx-q4f16` reste `accepted` sur un rerun de confirmation
- `ollama:qwen2.5:7b` finit soit `accepted`, soit `quality_blocked` avec un diagnostic resserre qui ne soit plus `outline_like`

### Risque principal
- la reference Apple 4B peut rester un succes isole si les switches runtime ou les budgets changent

### Dependances
- garder le garde-fou comme blocage dur
- conserver le protocole de comparaison commun et le meme preset qualite
- installer ou restager explicitement avant les reruns Apple:
  - `qwen2.5-0.5b-instruct-onnx`
  - `qwen3.5-4b-onnx-q4f16`
  - `stateful-mistral7b-instruct-int4-coreml`
- verifier avant chaque rerun Apple que le bon `model_id` est effectivement charge sur `:8201`

## Lot 2 - Tuner `rewrite` et `repair` pour Ollama 7B

### Objectif
- garder `apple-coreml:qwen3.5-4b-onnx-q4f16` comme reference
- faire passer `ollama:qwen2.5:7b` de `quality_blocked` a `accepted`
- ne garder les petits modeles que comme baselines vitesse ou regressions

### Ordre recommande
1. finir `apple-coreml:qwen2.5-0.5b-instruct-onnx`
2. finir `ollama:qwen2.5:1.5b`
3. rejouer `apple-coreml:qwen3.5-4b-onnx-q4f16`
4. rejouer `ollama:qwen2.5:7b`
5. `ollama:qwen3.5:9b` seulement si `qwen2.5:7b` termine un smoke complet

### Done quand
- le comparatif distingue clairement:
  - le modele de reference ANE actuel
  - le meilleur candidat Apple actuel
  - le meilleur candidat Ollama actuel
  - les baselines vitesse a conserver ou a sortir
  - le meilleur compromis Apple
  - le candidat vitesse encore insuffisant
  - les modeles a sortir de la reference locale

### Risque principal
- les meilleurs candidats peuvent rester meilleurs sur la qualite, mais encore hors reference tant que `rewrite` ne passe pas

### Dependances
- chemin Ollama de reference: Docker CPU via `mascarade`
- service Apple `:8201` stable pendant tout le smoke
- les trois modeles Apple cibles doivent etre installes et visibles cote runtime avant comparaison:
  - `qwen2.5-0.5b-instruct-onnx`
  - `qwen3.5-4b-onnx-q4f16`
  - `stateful-mistral7b-instruct-int4-coreml`
- temps borne par requete pour garder des verdicts comparables

## Lot 3 - Docs et runbooks finaux

### Objectif
- maintenir les README, TODOs, runbooks et le comparatif alignes sur l'etat reel

### Done quand
 - les docs distinguent clairement le modele `accepted`, les modeles `quality_blocked` et les baselines encore en rerun
- le comparatif et les runbooks renvoient tous vers ce plan du 8 mars 2026
- les TODOs n'exposent plus d'items deja livres

### Risque principal
- la doc redevient trop optimiste si elle est mise a jour avant la revalidation complete

### Dependances
- les lots 1 et 2 doivent produire des resultats reels, pas des suppositions

## Auto-sync
## Auto-sync
<!-- AUTO-SYNC:ANE-PLAN:START -->
- dernier verdict automatise: 2026-03-09T06:53:02+00:00
- accepted: aucun
- gate atteint: apple-coreml:qwen2.5-0.5b-instruct-onnx, ollama:qwen2.5:1.5b
- prochain lot calcule: Analyser les runs ayant atteint gate/repair puis resserrer la reference locale autour des meilleurs candidats.
- checkpoint manuel requis: Le runtime Apple sert `qwen2.5-0.5b-instruct-onnx` au lieu de `stateful-mistral7b-instruct-int4-coreml`.
<!-- AUTO-SYNC:ANE-PLAN:END -->
