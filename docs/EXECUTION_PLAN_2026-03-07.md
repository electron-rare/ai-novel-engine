# Plan d'execution - 7 mars 2026

Ordre recommande pour la suite de `ai-novel-engine`, base sur l'etat reel livre au 7 mars 2026.

## Lot 1 - Stabilisation locale Apple / Ollama

### Objectif
- verrouiller un run chapitre complet en local via `apple-coreml`
- rejouer le meme flux via `ollama`
- durcir la fin du pipeline sur les sorties JSON encore fragiles

### Done quand
- un chapitre complet passe jusqu'a la validation interactive puis a la promotion dans `manuscrit/` avec `apple-coreml`
- le meme chapitre passe avec `ollama` sans changer le pipeline narratif
- `critique` et `memory` disposent d'un second passage de reparation ou de reessai si le JSON reste invalide

### Risque principal
- le service Apple local `:8201` peut rester lent, bloquer une connexion ou degrader la validation sequentielle

### Dependances
- `mascarade` doit garder le shim `/v1/chat/completions` stable
- un backend `ollama` local doit etre disponible pour le second passage
- les budgets par etape doivent rester ajustables sans changer le pipeline

## Lot 2 - Workflow auteur et CLI non interactive

### Objectif
- rendre le workflow auteur exploitable en interactif et en batch local
- exposer plus clairement l'etat d'echec des chapitres

### Done quand
- `generate chapter` accepte `--approve` et `--reject`
- `status` expose les chapitres en echec, le dernier `failed_stage` et le dernier artefact utile
- le smoke local affiche un resume lisible sans ouvrir `meta.json`

### Risque principal
- la CLI peut devenir ambigue si les modes interactif et non interactif divergent

### Dependances
- les artefacts de pipeline doivent rester stables
- les metadonnees `meta.json` doivent contenir assez d'information pour alimenter `status`

## Lot 3 - Docs produit et runbooks

### Objectif
- remplacer les placeholders de doc produit
- figer les contrats cross-repo et les procedures de recuperation locales

### Done quand
- `docs/vision.md` et `docs/roadmap.md` ne sont plus des placeholders
- un runbook court de recuperation Apple local existe
- le contrat `mascarade` utile a `ai-novel-engine` est documente une fois, de facon stable

### Risque principal
- la doc peut diverger vite du runtime si elle est redigee avant la stabilisation locale

### Dependances
- le Lot 1 doit etre suffisamment stable pour produire des runbooks fiables
- `mascarade` doit figer le perimetre ANE suivi dans `TODO_AI_NOVEL_ENGINE.md`
