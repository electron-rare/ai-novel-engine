# Comparatif local ANE - 8 mars 2026

Comparatif realise avec le protocole courant:

- meme intention de smoke
- meme chapitre `02`
- meme CLI publique `generate chapter --chapter 02 --approve`
- meme preset qualite:
  - `ANE_MAX_TOKENS_STRUCTURE=256`
  - `ANE_MAX_TOKENS_DRAFT=768`
  - `ANE_MAX_TOKENS_CRITIQUE=512`
  - `ANE_MAX_TOKENS_REWRITE=768`
  - `ANE_MAX_TOKENS_GATE=384`
  - `ANE_MAX_TOKENS_REPAIR=512`
  - `ANE_MAX_TOKENS_MEMORY=320`
  - `ANE_REPAIR_MAX_PASSES=2`
- meme timeout borne par requete:
  - `300s`
- meme garde-fou manuscrit dur et meme boucle `repair`

Contexte machine:

- `ai-novel-engine` pointe vers `mascarade` sur `http://127.0.0.1:8100`
- `ai-novel-engine` resynchronise maintenant les tags Ollama via `127.0.0.1:11434`
- le host `ollama` natif 0.17.7 repond a `api/tags`, mais reste bloque en generation par un crash Metal sur cette machine
- pour rejouer les lots comparatifs Ollama, il faut rebrancher un chemin CPU stable cote Mascarade
- le runtime Apple local n'expose qu'un seul `model_id` a la fois sur `:8201`
- dernier cycle complet termine au 9 mars 2026:
  - `apple-coreml:qwen3.5-4b-onnx-q4f16` est `accepted`
  - `ollama:qwen2.5:7b` atteint `gate`, exerce `repair` puis finit `quality_blocked`
  - le lot `baselines` s'est termine separement avec deux `quality_blocked` sur `truncated_ending`

## Resultats

| Modele | Backend | Preflight | Smoke complet | Statut final | Derniere etape atteinte | Total observe | Prose / narration | JSON / controle | Verdict |
|---|---|---|---|---|---|---:|---|---|---|
| `apple-coreml:qwen3.5-4b-onnx-q4f16` | `apple-coreml` | OK | oui | `accepted` | `memory` | `711s` | meilleure nuance narrative du lot | critique exploitable, gate vert | reference ANE locale actuelle |
| `ollama:qwen2.5:7b` | `ollama` | OK | oui | `quality_blocked` | `gate` | `825s` | correcte, plus sobre que l'Apple 4B | critique exploitable, mais le texte reste trop proche d'un plan | meilleur candidat Ollama, encore bloque |
| `apple-coreml:qwen2.5-0.5b-instruct-onnx` | `apple-coreml` | OK | oui | `quality_blocked` | `gate` | `801s` | baseline vitesse Apple encore trop fragile pour la reference | `repair` actif, mais fin tronquee | baseline regression utile, pas reference qualite |
| `ollama:qwen2.5:1.5b` | `ollama` | OK | oui | `quality_blocked` | `gate` | `224s` | baseline vitesse correcte mais trop courte ou suspendue | `repair` actif, mais fin tronquee | temoin regression utile, pas candidat qualite |

Point legacy hors protocole courant:

| Modele | Backend | Preflight | Smoke complet | Statut final |
|---|---|---|---|---|
| `apple-coreml:stateful-mistral7b-instruct-int4-coreml` | `apple-coreml` | OK | bloque > `8 min` a `structure` | `archive hors chemin critique` |

## Lecture rapide

### `apple-coreml:qwen3.5-4b-onnx-q4f16`
- passe `structure`, `draft`, `critique`, `rewrite`, `gate` puis `memory`
- fournit le premier run `accepted` sous protocole `gate + repair`
- devient la reference ANE locale actuelle
- doit encore etre confirme sur rerun de stabilite

### `ollama:qwen2.5:7b`
- passe `structure`, `draft`, `critique`, `rewrite` puis `gate`
- exerce `repair` en live sur deux passes
- reste bloque sur `outline_like`
- c'est le meilleur candidat Ollama actuel, mais il lui manque encore une prose plus continue

### `apple-coreml:qwen2.5-0.5b-instruct-onnx`
- atteint `gate`, exerce `repair`, puis reste bloque sur `truncated_ending`
- reste utile comme candidat vitesse Apple, pas comme reference qualite

### `ollama:qwen2.5:1.5b`
- atteint `gate`, exerce `repair`, puis reste bloque sur `truncated_ending`
- reste un temoin de regression plus qu'un candidat qualite

## Verdicts

- **Modele de reference ANE**: `apple-coreml:qwen3.5-4b-onnx-q4f16`
- **Meilleur compromis Apple**: `apple-coreml:qwen3.5-4b-onnx-q4f16`
- **Meilleur compromis Ollama**: `ollama:qwen2.5:7b`
- **Modele rapide mais insuffisant**: `apple-coreml:qwen2.5-0.5b-instruct-onnx`
- **Modeles a eviter pour la redaction longue sur cette machine**: `ollama:qwen2.5:1.5b` et `apple-coreml:stateful-mistral7b-instruct-int4-coreml`

## Conclusion du cycle

Le cycle `priority_models` atteint enfin un objectif produit minimal:

- la boucle `repair` est implementée, testee et visible dans `status` / `meta.json`
- `repair` a maintenant une validation live sur `ollama:qwen2.5:7b`
- la reference Apple locale est reconfirmee sur deux runs comparables: `apple-coreml:qwen3.5-4b-onnx-q4f16`
- le prochain enjeu n'est plus de trouver un premier succes, mais de finir les baselines et de sortir `ollama:qwen2.5:7b` de `outline_like`

Le prochain lot logique n'est plus "ajouter un garde-fou", mais:

1. garder `automation/reports/apple_rerun_preset_20260313T223555Z` comme rerun Apple de reference pour les comparaisons futures
2. retablir un chemin Ollama CPU puis rejouer `priority_models` pour `ollama:qwen2.5:7b`
3. regler `rewrite` et `repair` pour faire tomber `outline_like` sur `ollama:qwen2.5:7b`
4. ne garder `qwen2.5-0.5b` et `qwen2.5:1.5b` que comme baselines vitesse ou regression

## Auto-sync
<!-- AUTO-SYNC:ANE-COMPARISON:START -->
- dernier cycle automatise: 2026-03-14T14:03:06+00:00

| Modele | Categorie | Preflight | Smoke | Classification | Failed stage | Gate | Repairs | Notes |
|---|---|---|---|---|---|---|---:|---|
| apple-coreml:qwen3.5-4b-onnx-q4f16 | priority_models | OK | oui | accepted |  | oui | 0 | Smoke manuel comparable rejoue avec les budgets preset du manifeste. |
| ollama:qwen2.5:7b | priority_models | KO | non | provider_failed |  | non | 0 | Le preflight Ollama natif a échoué.; HTTP 500 Internal Server Error |
| apple-coreml:qwen2.5-0.5b-instruct-onnx | baselines | OK | oui | quality_blocked | gate | oui | 2 |  |
| ollama:qwen2.5:1.5b | baselines | KO | non | provider_failed |  | non | 0 | Le preflight Ollama natif a échoué.; HTTP 500 Internal Server Error |
<!-- AUTO-SYNC:ANE-COMPARISON:END -->
