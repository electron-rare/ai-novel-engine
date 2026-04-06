# Memoire de reprise - 21 mars 2026

Memoire operationnelle pour reprendre `ai-novel-engine` sans refaire l'enquete docs/runtime/app.

## Etat code

- extraction lot 1/2/3 realisee : `core/runtime/` contient config, policies, client, health, checkpoints et preflight
- `core/evaluation/` ajoute un juge narratif secondaire activable par `ANE_JUDGE_MODEL`
- `core/generation/provider.py` garde le contrat public actuel mais repose maintenant sur la config runtime partagee
- `core/next_lots.py` et `scripts/ops_tui.py` consomment deja une partie des helpers runtime partages
- `core/tracking_sync.py` porte maintenant la synchronisation documentaire; `core/next_lots.py` est recentre sur orchestration + commandes
- `core/next_lots.py` ne porte plus directement la logique de checkpoint Apple ni le preflight HTTP Ollama natif
- le gate narratif peut maintenant fusionner heuristiques locales + verdict du juge secondaire
- suite Python verte : `155` tests

## Etat runtime utile

- reference actuelle : `apple-coreml:qwen3.5-4b-onnx-q4f16`
- candidat alternatif le plus credible : `ollama:qwen2.5:7b`
- les modeles 0.5b / 1.5b / mistral-nemo atteignent `gate` mais restent bloques sur la qualite narrative
- le point fragile reste la frontiere entre ANE et le shim OpenAI-compatible lorsque la sortie JSON doit etre structuree

## Etat docs utile

- nouveau point de reprise officiel :
  - `docs/CONTEXTE_PROJET_2026-03-21.md`
  - `docs/MEMOIRE_REPRISE_2026-03-21.md`
  - `docs/EXECUTION_PLAN_2026-03-21.md`
  - `docs/AGENTS_2026-03-21.md`
  - `docs/SYSTEM_SPEC_2026-03-21.md`
  - `docs/OSS_LANDSCAPE_2026-03-21.md`
- les docs app du 16 mars etaient stale par rapport au code; un rattrapage est requis
- les docs app ont ete rattrapees; la commande de test utile est `DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swift test`

## Logs / reports

- synthese reports : `python3 scripts/reports_ops.py summary`
- top erreurs : `python3 scripts/reports_ops.py analyze-logs --top 10`
- purge a garder en dry-run tant que les reports historiques cites dans la doc ne sont pas declasses

## Priorite immediate

1. Rejouer `priority_models` avec `ANE_JUDGE_MODEL` pour requalifier `qwen2.5:7b`.
2. Rejouer `french_models` avec `ANE_JUDGE_MODEL` pour requalifier `mistral-nemo`.
3. Continuer a garder `next_lots` concentre sur l'orchestration pure sans rouvrir la couche runtime.
4. Requalifier les TUIs/logs restants pour qu'ils lisent tous la meme couche runtime partagee.
