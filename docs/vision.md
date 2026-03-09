# Vision AI Novel Engine

## Positionnement

AI Novel Engine est un moteur narratif strict, local-first, pour projets longs.

Le but n'est pas de "discuter avec un chatbot qui écrit un roman". Le but est
de garder un pipeline lisible, reproductible et contrôlable par l'auteur:

`intention -> structure -> draft -> critique -> rewrite -> gate -> validation -> memoire`

## Ce que porte le produit

- l'auteur reste decisionnaire a chaque promotion vers le manuscrit
- aucune generation sans intention explicite
- aucune promotion vers le manuscrit si le garde-fou qualite bloque
- la memoire reste externe, inspectable et persistée sur disque
- les artefacts intermediaires sont lisibles en Markdown et JSON
- le moteur narratif reste decouple du runtime local

## Architecture cible

- `ai-novel-engine` porte la logique auteuriale, le pipeline, les prompts et la mémoire
- `mascarade` porte le runtime local, le routage provider et le shim OpenAI-compatible
- le contrat entre les deux reste minimal:
  - `POST /v1/chat/completions`
  - `model=provider:model`
  - non-streaming
  - JSON best effort, avec reessai applicatif cote ANE

## Non-objectifs v1

- chat libre comme interface principale
- studio web riche ou collaboratif
- autonomie complete "idee -> manuscrit final"
- base de donnees opaque pour la mémoire

## Critere de valeur

Le systeme est utile si un auteur peut:

- relancer un chapitre sans perdre le contexte de travail
- comprendre pourquoi une etape a echoue
- changer de backend local sans rewriter le pipeline narratif
- relire les brouillons, critiques et mises a jour memoire hors de l'IA
