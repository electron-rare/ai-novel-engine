# Principes

Principes simples qui doivent survivre aux changements de runtime, de prompts et d'outillage.

## Auteur d'abord

- l'auteur decide de l'intention
- l'auteur decide de la promotion manuscrit
- le systeme aide a ecrire, il ne remplace pas la direction du projet

## Lisibilite avant magie

- chaque etape doit laisser un artefact lisible
- chaque echec doit produire une trace compréhensible
- chaque lot automatique doit pouvoir etre repris

## Runtime decouple

- le pipeline narratif ne doit pas dependre d'un backend unique
- le contrat stable reste OpenAI-compatible
- les changements runtime ne doivent pas forcer une recriture auteuriale

## Guardrails reels

- pas de generation sans intention
- pas de manuscrit sans `gate`
- `repair` sert a sauver un brouillon, pas a contourner les regles

## Simplicite operationnelle

- TUI et scripts avant plateformes lourdes
- dry-run avant purge
- evidence avant intuition
