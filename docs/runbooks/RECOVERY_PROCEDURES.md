# Runbook Recovery - ANE

Procedures courtes de recuperation quand un lot est interrompu ou quand des artefacts JSON sont corrompus.

## 1) Reprendre un lot interrompu

```bash
python3 scripts/run_next_lots.py --resume automation/state/next_lots_state.json
```

## 2) Detecter un JSON corrompu

```bash
python3 -m json.tool brouillons/chapitres/chapitre_01/meta.json > /dev/null
```

## 3) Recovery metadata chapitre

```bash
cp brouillons/chapitres/chapitre_01/meta.json /tmp/meta_chapitre_01.backup.json
rm brouillons/chapitres/chapitre_01/meta.json
python3 -m cli.main generate chapter --chapter 01
```

## 4) Recovery automation state

```bash
cp automation/state/next_lots_state.json /tmp/next_lots_state.backup.json
rm automation/state/next_lots_state.json
python3 scripts/run_next_lots.py --lot priority_models
```

## 5) Logs et purge chirurgicale

```bash
python3 scripts/reports_ops.py analyze-logs --top 15
python3 scripts/reports_ops.py prune --days 14 --delete-workspaces
python3 scripts/reports_ops.py prune --days 14 --delete-workspaces --apply
```
