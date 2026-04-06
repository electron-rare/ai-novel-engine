# Gouvernance legere

Regles de gouvernance adaptees a un repo local-first, pilote par evidence.

## Source de verite

- le code et les tests priment
- les documents dates (`CONTEXTE`, `MEMOIRE_REPRISE`, `EXECUTION_PLAN`) servent de point de reprise
- les blocs `AUTO-SYNC` reflètent le dernier etat automatise, pas l'etat live instantane

## Priorisation

- runtime stable avant tuning prompts
- blockers produits avant optimisation cosmetique
- corrections chirurgicales avant refontes larges

## Changements

- un changement doit idealement livrer: code, verification, doc courte
- les suppressions de logs ou de reports se font d'abord en dry-run
- les docs ne doivent pas masquer un service down ou un lot incomplet

## Definition du done

- comportement verifie
- impact doc minimal mis a jour
- prochain pas explicite dans `TODO_ACTIVE.md` ou le plan courant
