# Audit du depot - 6 avril 2026

Audit rapide du depot principal `ai-novel-engine`, centre sur le moteur Python, les scripts d'exploitation et la documentation active.

## Verification effectuee

- `python3 -m unittest discover -s tests -v` -> `159` tests OK.
- `python3 scripts/reports_ops.py summary` -> `32` reports historises, avec `accepted=6`, `quality_blocked=15`, `provider_failed=9`.
- `python3 -m cli.main status` -> la CLI fonctionne, mais l'etat local courant expose encore un echec `structure`.
- `python3 -m cli.main generate chapter --chapter 01 --reject` -> echec immediat confirme sur conflit de fichiers d'intention.

## Findings

### P1 - Les points d'entree documentaires renvoient encore vers des snapshots perimes

Le `README` racine et `docs/dev/README.md` pointent encore majoritairement vers les snapshots du `16 mars 2026`, alors que le manifeste de suivi courant reference deja `docs/EXECUTION_PLAN_2026-03-22.md` et `docs/MODEL_COMPARISON_2026-03-22.md`, et que les derniers reports utiles sont du `23 mars 2026`.

Impact:
- un lecteur neuf repart sur une base trop ancienne
- la reference locale parait encore Apple dans plusieurs pages alors que l'`AUTO-SYNC` le plus recent remonte `mistral:mistral-large-latest`

References:
- `README.md`
- `docs/dev/README.md`
- `automation/next_lots.toml`

### P1 - La surface d'exploitation melange encore le chemin par defaut et le chemin alternatif runtime

Le manifeste courant route tout via `:8100` (`core_base_url` et `ollama_openai_base_url` pointent tous deux sur Mascarade), mais la documentation et certains raccourcis exposent encore `:8091` comme si c'etait la voie normale pour les smokes Ollama ou Mistral. En pratique, `:8091` n'est qu'un mode alternatif explicite quand on bascule vers `llama.cpp`.

Impact:
- risque de lancer un smoke sur le mauvais endpoint
- risque de contourner la politique runtime active du manifeste
- lecture plus difficile des incidents runtime

References:
- `automation/next_lots.toml`
- `README.md`
- `docs/runbooks/LOCAL_GENERATION.md`
- `Makefile`

### P1 - Le workspace courant contient un conflit de fichiers d'intention bloquant

Le depot contient a la fois `notes/intentions/chapitre_01.md` et `notes/intentions/chapitre_1.md`. Le moteur normalise bien les identifiants et refuse ce cas, mais cela bloque toute generation du chapitre `01` tant que le doublon n'est pas traite.

Impact:
- `generate chapter --chapter 01` echoue avant meme l'appel provider
- le probleme ressemble a un souci runtime si on ne teste pas explicitement la commande

References:
- `notes/intentions/chapitre_01.md`
- `notes/intentions/chapitre_1.md`

### P2 - `status` n'aide pas encore assez a diagnostiquer l'etat projet

La commande `status` affiche la section `Dossiers`, mais elle montre en fait des booleens d'existence et non des chemins. Elle ne remonte pas non plus les conflits de fichiers de chapitre, alors que ceux-ci bloquent ensuite `generate`.

Impact:
- UX trompeuse pour l'onboarding et le diagnostic local
- il manque un signal preventif sur les conflits `chapitre_01` / `chapitre_1`

References:
- `cli/main.py`
- `core/project/loader.py`

## Recommandations

1. Utiliser `docs/dev/README.md` comme index vivant et y pointer vers les derniers docs dates, pas vers les snapshots historiques par defaut.
2. Distinguer partout le chemin par defaut `:8100` et le chemin alternatif `:8091`.
3. Standardiser les fichiers chapitre en forme canonique `chapitre_01.md`, `chapitre_02.md`, etc.
4. Faire evoluer ensuite `status` pour remonter les conflits de chapitres avant `generate`.

## Actions documentaires appliquees dans ce lot

- mise a jour du `README` racine
- remise a niveau de `docs/dev/README.md`
- clarification du runbook `docs/runbooks/LOCAL_GENERATION.md`
- actualisation de `docs/roadmap.md`
