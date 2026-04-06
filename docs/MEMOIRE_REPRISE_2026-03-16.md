# Memoire de reprise - 16 mars 2026

Memoire operationnelle pour reprendre `ai-novel-engine` sans refaire l'enquete runtime ni l'audit repo.

## Etat code

- suite unitaire verte: `55` tests
- derniere passe: ajout d'un module partage de reporting, d'un TUI ops, et d'un fix de deduplication chronologie
- scripts d'exploitation Python executes directement depuis `scripts/` corriges pour resoudre le repo root avant import

## Etat runtime utile

- `:8201` repond et sert `qwen3.5-4b-onnx-q4f16`
- `:11434/api/tags` repond et les blobs `qwen2.5` sont bien presents
- `:8100` ne repond pas actuellement
- `:8091` ne repond pas actuellement

## Etat produit utile

- reference accepted: `apple-coreml:qwen3.5-4b-onnx-q4f16`
- baseline Apple regression: `apple-coreml:qwen2.5-0.5b-instruct-onnx` -> `quality_blocked`
- meilleur candidat alternatif: `ollama:qwen2.5:7b`
- preuve importante de reprise: `ollama:qwen2.5:1.5b` a deja atteint `gate` via `llama-server`; il n'est donc plus seulement a lire comme un echec provider

## Nouveaux points d'appui

- `scripts/ops_tui.py` pour suivre projet, automation, reports, erreurs stderr et empreinte disque
- `scripts/reports_ops.py analyze-logs` corrige pour afficher les vrais modeles au lieu de noms deformes
- `core/reporting.py` centralise la lecture des `run.json`, le comptage des classifications et l'agregation d'erreurs logs

## Risques a ne pas oublier

- ne pas relancer des lots entiers tant que `:8100` n'est pas revenu
- ne pas considerer `qwen2.5:7b` comme "qualite bloquee" tant qu'on n'a pas un rerun complet via le nouveau chemin runtime
- ne pas laisser les reruns du meme chapitre dupliquer la chronologie; le correctif est maintenant pose mais doit etre garde

## Commandes utiles

```bash
python3 scripts/ops_tui.py --watch --interval 3
python3 scripts/next_lots_tui.py --watch --interval 2
python3 scripts/reports_ops.py summary
python3 scripts/reports_ops.py analyze-logs --top 10
python3 scripts/run_next_lots.py --resume automation/state/next_lots_state.json
```

## Priorite immediate

1. Remonter `:8100`.
2. Remonter `:8091` si un lot `ollama:*` est a rejouer.
3. Valider `qwen2.5:7b` via le meme chemin que `qwen2.5:1.5b`.
4. Rejouer `priority_models`, puis `baselines`.
