# Runbook Automation

Runbook court pour piloter `next_lots`, lire les reports et nettoyer sans casser l'historique utile.

## Vue d'ensemble

- orchestrateur: `python3 scripts/run_next_lots.py`
- TUI lot courant: `python3 scripts/next_lots_tui.py --watch --interval 2`
- TUI ops global: `python3 scripts/ops_tui.py --watch --interval 3`
- TUI remote Mascarade: `python3 scripts/mascarade_remote_tui.py --watch --interval 4`
- synthese reports: `python3 scripts/reports_ops.py summary`
- analyse logs: `python3 scripts/reports_ops.py analyze-logs --top 10`

## Boucle recommandee

```bash
python3 scripts/ops_tui.py --watch --interval 3
python3 scripts/next_lots_tui.py --watch --interval 2
```

Quand un checkpoint apparait:

1. lire la raison dans le TUI
2. executer la commande preparee
3. reprendre avec `python3 scripts/run_next_lots.py --resume automation/state/next_lots_state.json`

## Lots utiles

```bash
python3 scripts/run_next_lots.py --lot priority_models
python3 scripts/run_next_lots.py --lot baselines
python3 scripts/run_next_lots.py --lot tracking_sync
python3 scripts/run_next_lots.py --lot full
```

## Logs

Lecture rapide:

```bash
python3 scripts/reports_ops.py analyze-logs --top 10
```

Ce que l'outil fait maintenant:

- agrege les erreurs `STDERR`
- rattache les logs aux vrais modeles via `run.json`
- evite les pseudo-noms deformes du style `ollama:qwen2:5:7b`

## Purge chirurgicale

Toujours commencer par un dry-run:

```bash
python3 scripts/reports_ops.py prune --days 14
python3 scripts/reports_ops.py prune --days 14 --delete-workspaces
```

Suppression effective seulement si la retention est claire:

```bash
python3 scripts/reports_ops.py prune --days 14 --delete-workspaces --apply
```

Regle:

- ne pas supprimer les reports encore utiles au comparatif courant
- preferer supprimer d'abord les `workspaces/` anciens si l'on veut alleger sans perdre `run.json` et les logs

## Commandes de reprise runtime

- runtime Apple seulement: verifier `http://127.0.0.1:8201/models`
- runtime `llama.cpp`: utiliser `bash ./scripts/prepare_llama_cpp_runtime.sh --model qwen2.5:7b --port 8091`
- reprendre ensuite le lot ANE avec `--resume`

## Multi-host Mascarade (tower / kxkm)

Config centralisee:

```bash
cat automation/mascarade_hosts.toml
```

Cockpit distant:

```bash
python3 scripts/mascarade_remote_tui.py --watch --interval 4
```

Tunnel manuel (exemples):

```bash
ssh -N -L 127.0.0.1:8110:127.0.0.1:8100 clems@192.168.120
ssh -N -L 127.0.0.1:8111:127.0.0.1:8100 kxkm@kxkm-ai
```

## Persistance launchd (macOS)

```bash
python3 scripts/setup_mascarade_launchd.py render
python3 scripts/setup_mascarade_launchd.py install --dry-run
python3 scripts/setup_mascarade_launchd.py install
python3 scripts/setup_mascarade_launchd.py status
```

Plists de reference versionnes:

- `automation/launchd/com.ai-novel-engine.mascarade.tower.tunnel.plist`
- `automation/launchd/com.ai-novel-engine.mascarade.kxkm.tunnel.plist`
