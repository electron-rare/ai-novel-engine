# Memoire de reprise - 13 mars 2026

Memoire operationnelle courte pour reprendre `ai-novel-engine` sans relire tout le repo.

## Etat confirme

- la suite locale est saine: `python3 -m unittest discover -s tests -v` passe avec `44` tests
- le pipeline auteur reste le meme: `intention -> structure -> draft -> critique -> rewrite -> gate -> validation -> memoire`
- le lot `priority_models` du `2026-03-09T05:54:57Z` a donne:
  - `apple-coreml:qwen3.5-4b-onnx-q4f16` -> `accepted`
  - `ollama:qwen2.5:7b` -> `quality_blocked` avec residu `outline_like`
- le rerun comparable `automation/reports/apple_rerun_preset_20260313T223555Z` a fini `accepted` le 13 mars 2026 avec `repair_attempts=0` et un `draft_v2` de `323` mots
- le lot `baselines` du `2026-03-09T06:35:12Z` a donne:
  - `apple-coreml:qwen2.5-0.5b-instruct-onnx` -> `quality_blocked` avec `truncated_ending`
  - `ollama:qwen2.5:1.5b` -> `quality_blocked` avec `truncated_ending`
- l'etat automatise a ete cloture proprement le `2026-03-13T14:15:56+00:00`
- `stateful-mistral7b-instruct-int4-coreml` est sorti du chemin critique; il ne bloque plus `full`
- etat runtime relu le 13 mars 2026 au soir:
  - `http://127.0.0.1:8100/health` repond de nouveau
  - `http://127.0.0.1:8201/health` et `http://127.0.0.1:8201/models` repondent de nouveau
  - `http://127.0.0.1:11434/api/tags` repond de nouveau
  - `mascarade-core` et `mascarade-api` ont ete recrees avec `OLLAMA_BASE_URL=http://host.docker.internal:11434`
  - le vrai blocage live restant n'est plus un port mort mais `ollama` natif 0.17.7, qui echoue encore en generation sur `qwen2.5:7b` et `qwen2.5:1.5b` avec une erreur Metal
  - le rerun Apple comparable `automation/reports/apple_rerun_7oY51o` n'a pas reconfirme la reference: il a atteint `gate`, a ete bloque par `too_short` + `truncated_ending`, puis a echoue a `repair` a cause de l'ancien fallback pipeline vers l'Ollama natif

## Contradiction resolue

Le repo avait deux verites concurrentes:

- les rapports `priority_models` montraient un vrai modele `accepted`
- les sections `AUTO-SYNC` les plus recentes perdaient cette information des qu'un lot partiel plus recent ecrasait le `state` courant

Le suivi a ete corrige pour consolider les derniers resultats connus par modele depuis `automation/reports/*/run.json`. Le prochain `tracking_sync` ne doit plus oublier la reference `apple-coreml:qwen3.5-4b-onnx-q4f16`.

## Decisions de reprise

- fixer `apple-coreml:qwen3.5-4b-onnx-q4f16` comme reference locale reconfirmee sur deux runs comparables (`20260309T055457Z` puis `apple_rerun_preset_20260313T223555Z`)
- traiter `ollama:qwen2.5:7b` comme meilleur candidat alternatif a faire sortir de `outline_like`
- garder `apple-coreml:qwen2.5-0.5b-instruct-onnx` et `ollama:qwen2.5:1.5b` comme baselines vitesse et regression, pas comme references qualite
- garder `stateful-mistral7b-instruct-int4-coreml` hors chemin critique tant qu'un besoin produit explicite ne justifie pas sa reintroduction

## Fichiers a regarder en premier

- `automation/state/next_lots_state.json`
- `automation/reports/20260309T055457Z/SUMMARY.md`
- `automation/reports/20260309T063512Z/SUMMARY.md`
- `automation/reports/apple_rerun_preset_20260313T223555Z/brouillons/chapitres/chapitre_02/`
- `automation/reports/20260309T055457Z/workspaces/ollama_qwen2_5_7b/brouillons/chapitres/chapitre_02/`
- `automation/reports/20260309T063512Z/workspaces/apple_coreml_qwen2_5_0_5b_instruct_onnx/brouillons/chapitres/chapitre_02/`
- `automation/reports/20260309T063512Z/workspaces/ollama_qwen2_5_1_5b/brouillons/chapitres/chapitre_02/`

## Commandes utiles

```bash
python3 -m unittest discover -s tests -v
python3 scripts/run_next_lots.py --lot tracking_sync --report-only
python3 scripts/run_next_lots.py --lot priority_models
```

## Prochaine hypothese de travail

Le prochain gain utile ne viendra pas d'un nouveau backend mais d'un meilleur controle de `rewrite` et `repair`:

- `ollama:qwen2.5:7b` doit perdre le residu planifie `outline_like`
- les petites baselines doivent finir proprement sans `truncated_ending`
- la reference Apple 4B est reconfirmee; la priorite live se deplace maintenant vers `ollama:qwen2.5:7b`
- la priorite live n'est plus de rallumer `:8100` et `:8201`, mais de retablir un chemin Ollama CPU stable; le rerun Apple ne bascule plus par defaut vers Ollama pendant `repair`
