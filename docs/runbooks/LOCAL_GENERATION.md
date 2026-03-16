# Runbook local - generation ANE

Runbook court pour lancer et diagnostiquer la generation locale via `mascarade`.

Comparatif de reference: [`docs/MODEL_COMPARISON_2026-03-08.md`](../MODEL_COMPARISON_2026-03-08.md)

## Prerequis

- `mascarade` repond sur `http://127.0.0.1:8100/health`
- le modele reste explicite via `ANE_MODEL` ou `--model`
- une intention existe pour le chapitre cible
- le garde-fou manuscrit et la boucle `repair` peuvent bloquer la promotion meme avec `--approve`

## Cycle automatise

Commande de reference:

```bash
python3 scripts/run_next_lots.py --lot full
```

Commandes utiles:

```bash
python3 scripts/run_next_lots.py --lot priority_models
python3 scripts/run_next_lots.py --resume automation/state/next_lots_state.json
python3 scripts/run_next_lots.py --lot tracking_sync --report-only
```

Le driver:
- lit `automation/next_lots.toml`
- rejoue preflights et smokes dans l'ordre utile du moment
- met a jour les sections `AUTO-SYNC` des TODOs, plans, README et runbooks
- attend brievement que `/models` reflète le bon `model_id` apres un switch Apple avant de recréer un checkpoint manuel
- s'arrete proprement si un restart runtime ou un switch Apple est requis, puis imprime la commande de reprise

## Contrat local

`ai-novel-engine` parle uniquement a `mascarade` sur `POST /v1/chat/completions`.

- format modele: `provider:model`
- dernier cycle complet termine au 9 mars 2026:
  - `apple-coreml:qwen3.5-4b-onnx-q4f16` est `accepted` de bout en bout sous garde-fou
  - `ollama:qwen2.5:7b` atteint `gate`, exerce `repair` en live, puis finit `quality_blocked` sur `outline_like`
  - `apple-coreml:stateful-mistral7b-instruct-int4-coreml` est retire du chemin critique et garde comme reference experimentale
- rerun comparable du 13 mars 2026:
  - `automation/reports/apple_rerun_preset_20260313T223555Z` est `accepted` sans `repair` et reconfirme la reference Apple locale
- le lot `baselines` pour `apple-coreml:qwen2.5-0.5b-instruct-onnx` et `ollama:qwen2.5:1.5b` a ete rejoue separement; les deux modeles restent `quality_blocked` sur `truncated_ending`
- le runtime Apple local ne sert qu'un seul `model_id` a la fois
- le fallback `repair` n'essaie plus de changer de modele `apple-coreml` en plein smoke; tout switch Apple reste une action runtime explicite

## Smoke Apple

Preflight minimal cote runtime:

```bash
bash /Users/electron/mascarade/scripts/smoke_openai_compat_ane.sh \
  --url http://127.0.0.1:8100 \
  --model "apple-coreml:qwen3.5-4b-onnx-q4f16"
```

Smoke chapitre complet:

```bash
./scripts/smoke_local_generation.sh \
  --base-url http://127.0.0.1:8100 \
  --model "apple-coreml:qwen3.5-4b-onnx-q4f16" \
  --approve
```

Notes:
- le script fait un warm-up automatique via `:8100` quand le modele commence par `apple-coreml:`
- le premier chargement Core ML peut etre long
- le smoke Apple applique par defaut un timeout plus large et des budgets plus courts; utiliser `--timeout` ou `ANE_MAX_TOKENS_*` pour durcir ou assouplir
- `ANE_MAX_TOKENS_GATE` permet de regler le budget du garde-fou LLM
- `ANE_MAX_TOKENS_REPAIR` et `ANE_REPAIR_MAX_PASSES` reglent la boucle `repair`
- `apple-coreml:qwen2.5-0.5b-instruct-onnx` reste le candidat vitesse Apple a requalifier en baseline
- `apple-coreml:qwen3.5-4b-onnx-q4f16` est la reference Apple locale actuelle, reconfirmee par `apple_rerun_preset_20260313T223555Z`
- `apple-coreml:stateful-mistral7b-instruct-int4-coreml` reste archive hors lot utile sur cette machine: il repond, mais le smoke ANE est reste bloque a `structure` pendant plus de 8 minutes

## Smoke Ollama

Preflight:

```bash
bash /Users/electron/mascarade/scripts/smoke_openai_compat_ane.sh \
  --url http://127.0.0.1:8100 \
  --model "ollama:qwen2.5:1.5b"
```

Le provider `ollama` doit apparaitre dans `providers` et le modele cible doit etre deja installe.
Sur cette machine, le meilleur candidat Ollama courant est `ollama:qwen2.5:7b`; `qwen2.5:1.5b` reste une baseline de regression, pas un candidat qualite.

Smoke chapitre complet:

```bash
./scripts/smoke_local_generation.sh \
  --base-url http://127.0.0.1:8100 \
  --model "ollama:qwen2.5:1.5b" \
  --approve
```

## Lire rapidement le resultat

Le smoke affiche un resume humain:

- `backend`
- `chapter`
- `status`
- `accepted`
- `failed_stage` si present
- `quality_blockers` si presents
- `retry_stages` si present
- `repair_attempts` et `repair_models` si presents
- chemins vers `draft_v2`, `repair_latest`, `critique_v1`, `gate_v1`, `manuscript`, `memory_summary`, `meta.json`

Le fichier de reference reste:

```bash
cat brouillons/chapitres/chapitre_XX/meta.json
```

Champs utiles:
- `status`
- `last_status_message`
- `stage_attempts`
- `retry_stages`
- `failed_stage`
- `quality_blockers`
- `repair_attempts`
- `repair_models`
- `gate_report`
- `provider.base_url`
- `provider.model`

## Etat auto-synchronise
<!-- AUTO-SYNC:ANE-RUNBOOK:START -->
- dernier cycle automatise: 2026-03-14T14:03:06+00:00
- chapitre courant detecte: chapitre_01
- reference locale actuelle: apple-coreml:qwen3.5-4b-onnx-q4f16
- prochain lot utile: Reference locale reconfirmee; retablir le runtime des modeles provider_failed puis reprendre rewrite/repair sur les modeles bloques a gate.
<!-- AUTO-SYNC:ANE-RUNBOOK:END -->
