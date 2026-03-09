# AI Novel Engine

AI Novel Engine est un moteur de rédaction de romans assisté par IA.

Il ne génère pas de romans.
Il fournit une méthode, une architecture et des outils
pour permettre aux écrivains de tenir des projets narratifs longs
sans perte de cohérence, de mémoire ou de contrôle.

## Principes clés
- l’auteur reste décisionnaire
- aucune génération sans intention
- l’IA est découpée en rôles
- la mémoire est externe
- la simplicité est une contrainte

## Statut
v2 — développement en cours (open-source)

## Suivi
- backlog actif: [`TODO_ACTIVE.md`](./TODO_ACTIVE.md)
- etat livre: [`TODO_IMPLEMENTE.md`](./TODO_IMPLEMENTE.md)
- ordre d'execution recommande: [`docs/EXECUTION_PLAN_2026-03-08.md`](./docs/EXECUTION_PLAN_2026-03-08.md)
- runbook local: [`docs/runbooks/LOCAL_GENERATION.md`](./docs/runbooks/LOCAL_GENERATION.md)
- comparatif modeles local: [`docs/MODEL_COMPARISON_2026-03-08.md`](./docs/MODEL_COMPARISON_2026-03-08.md)

## Automation des lots utiles

Le driver principal des prochains lots utiles est maintenant:

```bash
python3 scripts/run_next_lots.py --lot full
```

Points clés:
- le manifeste versionné est `automation/next_lots.toml`
- le driver réutilise les smokes existants au lieu de dupliquer le pipeline
- les opérations sensibles restent semi-autos: en cas de switch Apple ou de restart runtime, le cycle prépare les commandes exactes puis s'arrête avec un état de reprise
- reprise:

```bash
python3 scripts/run_next_lots.py --resume automation/state/next_lots_state.json
```

- synchronisation seule des plans/TODOs/readmes à partir du dernier état:

```bash
python3 scripts/run_next_lots.py --lot tracking_sync --report-only
```

## Generation locale via Mascarade

`ai-novel-engine` parle un provider OpenAI-compatible. Pour utiliser la
generation locale via `mascarade`, pointer simplement le moteur narratif vers le
core Python sur `:8100`.

```bash
export ANE_PROVIDER=openai_compatible
export ANE_BASE_URL=http://127.0.0.1:8100
export ANE_MODEL=<provider:model>
export ANE_MAX_TOKENS=512
export ANE_MAX_TOKENS_STRUCTURE=256
export ANE_MAX_TOKENS_DRAFT=512
export ANE_MAX_TOKENS_CRITIQUE=384
export ANE_MAX_TOKENS_REWRITE=512
export ANE_MAX_TOKENS_GATE=320
export ANE_MAX_TOKENS_REPAIR=384
export ANE_MAX_TOKENS_MEMORY=256
export ANE_REPAIR_MAX_PASSES=2
# optionnel si tu veux forcer un fallback explicite pour la reparation
# export ANE_REPAIR_FALLBACK_MODEL=ollama:qwen2.5:7b

# seulement si MASCARADE_API_KEY est active
export ANE_API_KEY=ton-token-mascarade

python3 -m cli.main generate chapter --chapter 01
```

Notes :
- `ANE_MODEL` est requis; le repo n'impose pas de modele par défaut
- `ANE_MODEL` selectionne le backend local par prefixe `apple-coreml:` ou `ollama:`
- `ANE_MAX_TOKENS` reste le plafond global par défaut
- les overrides `ANE_MAX_TOKENS_STRUCTURE`, `..._DRAFT`, `..._CRITIQUE`, `..._REWRITE`, `..._GATE`, `..._REPAIR`, `..._MEMORY` permettent d'ajuster chaque étape
- `ANE_REPAIR_MAX_PASSES` borne la boucle `repair`
- `ANE_REPAIR_FALLBACK_MODEL` permet de forcer le modele du second passage `repair`
- le pipeline narratif reste entierement dans `ai-novel-engine`
- `mascarade` sert uniquement de runtime local et de couche OpenAI-compatible
- dernier cycle complet termine au 9 mars 2026 :
  - `apple-coreml:qwen3.5-4b-onnx-q4f16` est `accepted` de bout en bout sous garde-fou
  - `ollama:qwen2.5:7b` atteint `gate`, exerce `repair` en live, puis finit `quality_blocked` sur `outline_like`
  - `apple-coreml:stateful-mistral7b-instruct-int4-coreml` reste `preflight_only`
- les baselines `apple-coreml:qwen2.5-0.5b-instruct-onnx` et `ollama:qwen2.5:1.5b` sont en rerun automatise separe; ils ne sont plus la reference locale courante
- le smoke et `status` exposent maintenant `gate_v1.json`, `quality_blockers`, `failed_stage`, `repair_attempts` et `repair_models`
- le runtime Apple local ne sert qu'un `model_id` a la fois; un fallback `repair` vers un autre modele Apple exige donc un switch de service entre runs

Smoke test local rapide :

```bash
./scripts/smoke_local_generation.sh \
  --base-url http://127.0.0.1:8100 \
  --model "ollama:qwen2.5:1.5b" \
  --approve
```

Le script cree un workspace temporaire, ecrit une intention de test, lance la vraie CLI publique, fait un warm-up automatique pour `apple-coreml`, puis affiche un resume humain des artefacts et du `meta.json`. En mode `apple-coreml`, il applique par defaut un timeout plus large (`ANE_TIMEOUT=900`) et des budgets de smoke plus courts pour eviter de faire exploser la latence locale. Pour les reruns qualitatifs de reference, fixer explicitement `--timeout 300` et des budgets `ANE_MAX_TOKENS_*` communs. Utiliser `--workspace`, `--chapter`, `--intention`, `--timeout`, `--approve` ou `--reject` si besoin.

## Etat auto-synchronise
## Etat auto-synchronise
<!-- AUTO-SYNC:ANE-README:START -->
- dernier cycle automatise: 2026-03-09T06:53:02+00:00
- reference locale actuelle: aucun accepted, meilleur diagnostic: apple-coreml:qwen2.5-0.5b-instruct-onnx
- prochain lot utile: Analyser les runs ayant atteint gate/repair puis resserrer la reference locale autour des meilleurs candidats.
- lancer un cycle: `python3 scripts/run_next_lots.py --lot full`
- checkpoint manuel en attente: Le runtime Apple sert `qwen2.5-0.5b-instruct-onnx` au lieu de `stateful-mistral7b-instruct-int4-coreml`.
<!-- AUTO-SYNC:ANE-README:END -->
