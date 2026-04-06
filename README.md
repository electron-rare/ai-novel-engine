# AI Novel Engine

Le cockpit d'ecriture pour romans assistes par IA.

AI Novel Engine rassemble une application macOS de pilotage editorial et un moteur narratif structure pour aider un auteur a tenir un projet long sans perdre la main. Le projet n'est pas un chatbot qui "pond un roman". C'est un environnement de travail pour cadrer un livre, faire circuler le bon contexte, comparer les versions, lancer des assistants specialises, puis ne promouvoir que ce qui merite vraiment d'entrer dans le manuscrit.

## Ce que le produit apporte

- une application Studio pour piloter projet, scenes, personnages, arcs et dependances
- une assistance a l'ecriture a plusieurs niveaux: inline, copilote, agents, pipeline complet
- une logique local-first avec artefacts lisibles, historiques et diffables
- un garde-fou narratif avant toute promotion dans le manuscrit
- une separation claire entre assistance, generation, validation et memoire projet

## Une assistance a l'ecriture vraiment pilotee

AI Novel Engine aide a ecrire de quatre manieres complementaires:

- assistance inline sur les champs editoriaux majeurs: titre, genre, logline, synopsis, note auteur, fiches personnages, objectifs de scene et brouillons
- `Copilot / Writing Tools` pour converser, resumer, relire, proposer un rewrite et comparer brouillon, reponse assistant et dernier manuscrit pipeline
- `Wizard Agents` pour choisir un agent Mascarade, preparer un brief, verifier le routage et reappliquer la sortie avec tracabilite
- pipeline ANE complet pour passer d'une intention a un chapitre relu, gate et eventuellement promu

L'idee centrale: chaque niveau d'assistance a son role. On n'utilise pas le meme outil pour trouver un titre, debloquer une scene, challenger une incoherence ou fabriquer un chapitre entier sous contrainte.

## Ce que l'application permet aujourd'hui

### Piloter le roman

- organiser des projets locaux avec bibliotheque, sauvegarde et reprise
- travailler scene par scene avec objectifs, beat, mood, cible de mots et brouillon
- suivre personnages, arcs et dependances entre scenes
- garder visibles les signaux pipeline, les blockers et les artefacts utiles

### Ecrire avec contexte

- injecter le contexte editorial utile dans les aides inline
- lancer un copilote avec historique local par projet
- utiliser un RAG local-first qui recoupe scene, brouillons, gate pipeline, manuscrit et sorties agent
- comparer avant application plutot que remplacer a l'aveugle

### Orchestrer l'IA au bon niveau

- prioriser Apple Intelligence quand elle est disponible
- basculer sur OpenAI, Mascarade ou un runtime local compatible OpenAI
- gerer les presets runtime et les modeles locaux MLX depuis l'app
- lancer des agents Mascarade et rejouer leurs sorties dans le flux d'ecriture

### Garder le controle

- confirmations avant les ecritures destructives
- lecture du gate, des blockers et des recommandations pipeline
- promotion vers le manuscrit seulement quand le chapitre passe les garde-fous et la validation auteur
- persistance locale des projets et artefacts lisibles sur disque

## Le coeur du projet

Le repo combine deux couches qui travaillent ensemble:

- `app_AI-novel-engine/`: le Studio macOS SwiftUI, centre de pilotage de l'assistance a l'ecriture
- le repo racine Python: le moteur narratif ANE, la CLI, les prompts, l'orchestration runtime, le reporting et les runbooks

Le workflow narratif reste volontairement explicite:

`intention -> structure -> draft -> critique -> rewrite -> gate -> validation auteur -> memoire`

## Pourquoi c'est different

- l'auteur reste decisionnaire
- aucune generation sans intention
- l'IA est decoupee en roles au lieu d'etre une seule boite noire
- la memoire projet reste externe et inspectable
- l'application aide a piloter l'ecriture, pas a effacer le travail editorial

Manifeste operationnel:
- principes: [`docs/principes.md`](./docs/principes.md)
- gouvernance: [`docs/governance.md`](./docs/governance.md)

## Demarrage rapide

### Lancer le moteur et verifier le repo

```bash
python3 -m unittest discover -s tests -v
python3 -m cli.main status
make healthcheck
python3 scripts/reports_ops.py summary
```

### Lancer l'application macOS

```bash
cd app_AI-novel-engine
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swift build
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swift run
```

Pour lancer un vrai bundle `.app`:

```bash
cd app_AI-novel-engine
./scripts/studio_ops.sh run-app
```

### Lancer un smoke narratif local

```bash
./scripts/smoke_local_generation.sh \
  --base-url http://127.0.0.1:8100 \
  --model "<provider:model>" \
  --approve
```

## Surfaces principales du repo

- `cli/`: CLI publique du moteur narratif
- `core/`: pipeline, runtime, reporting, automation et logique projet
- `scripts/`: smokes, TUIs, supervision et helpers ops
- `tests/`: suite Python unitaire
- `prompts/`: prompts versionnes
- `docs/`: runbooks, specs, snapshots, audit et index
- `app_AI-novel-engine/`: Studio macOS SwiftUI

## Reperes utiles

- index documentaire vivant: [`docs/dev/README.md`](./docs/dev/README.md)
- audit courant: [`docs/CODE_AUDIT_2026-04-06.md`](./docs/CODE_AUDIT_2026-04-06.md)
- backlog actif: [`TODO_ACTIVE.md`](./TODO_ACTIVE.md)
- etat livre: [`TODO_IMPLEMENTE.md`](./TODO_IMPLEMENTE.md)
- runbook generation locale: [`docs/runbooks/LOCAL_GENERATION.md`](./docs/runbooks/LOCAL_GENERATION.md)
- runbook automation: [`docs/runbooks/AUTOMATION.md`](./docs/runbooks/AUTOMATION.md)
- workflow narratif: [`docs/workflow.md`](./docs/workflow.md)
- manifeste d'exploitation: [`automation/next_lots.toml`](./automation/next_lots.toml)

## Notes d'exploitation

- le chemin par defaut du manifeste courant passe par `:8100`
- `:8091` est un chemin alternatif explicite pour `llama.cpp`, pas la voie normale tant que le manifeste ne pointe pas dessus
- `ANE_MODEL` reste obligatoire pour les smokes et la CLI provider-compatible
- le runtime Apple reste mono-modele; certains switches demandent encore une action manuelle
- les blocs `AUTO-SYNC` donnent le dernier etat automatise connu, pas l'etat live instantane
- les fichiers chapitre doivent rester canoniques: `chapitre_01.md`, `chapitre_02.md`, etc.

## Automation et supervision

```bash
python3 scripts/run_next_lots.py --lot full
python3 scripts/run_next_lots.py --resume automation/state/next_lots_state.json
python3 scripts/run_next_lots.py --lot tracking_sync --report-only
python3 scripts/next_lots_tui.py --watch --interval 2
python3 scripts/ops_tui.py --watch --interval 3
```

La supervision, les reports et la purge sont documentes dans [`docs/runbooks/AUTOMATION.md`](./docs/runbooks/AUTOMATION.md).

## Etat auto-synchronise
<!-- AUTO-SYNC:ANE-README:START -->
- dernier cycle automatise: 2026-03-23T21:34:05+00:00
- reference locale actuelle: mistral:mistral-large-latest
- prochain lot utile: Reference locale reconfirmee; retablir le runtime des modeles provider_failed avant de poursuivre.
- lancer un cycle: `python3 scripts/run_next_lots.py --lot full`
- checkpoint manuel en attente: Le runtime Apple sert `aucun modèle` au lieu de `qwen3-4b-instruct-2507-q4f16`.
<!-- AUTO-SYNC:ANE-README:END -->
