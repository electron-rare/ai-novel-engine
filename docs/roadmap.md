# Roadmap v2

Roadmap courte et concrete, remise a niveau apres audit du 6 avril 2026.

## Priorite 1 - Remettre les points d'entree au propre

- garder un index doc vivant dans `docs/dev/README.md`
- distinguer partout le chemin par defaut `:8100` du chemin alternatif `:8091`
- eviter les contradictions entre historique Apple, `AUTO-SYNC` courant et reports les plus recents

## Priorite 2 - Assainir le workspace et le diagnostic local

- supprimer les doublons de chapitres non canoniques du type `chapitre_1.md`
- faire remonter ces conflits plus tot dans `status`
- clarifier les sorties de statut quand un dossier existe mais n'est pas encore exploitable

## Priorite 3 - Reprendre les reruns utiles

- retablir les providers encore `provider_failed`
- rejouer les lots utiles depuis `automation/state/next_lots_state.json` quand le runtime Apple et les providers distants sont prets
- garder les modeles Apple et Ollama explicites dans les smokes et les reports

## Source de verite

- index dev: [`dev/README.md`](./dev/README.md)
- audit: [`CODE_AUDIT_2026-04-06.md`](./CODE_AUDIT_2026-04-06.md)
- contexte courant: [`CONTEXTE_PROJET_2026-03-22.md`](./CONTEXTE_PROJET_2026-03-22.md)
- memoire de reprise: [`MEMOIRE_REPRISE_2026-03-22.md`](./MEMOIRE_REPRISE_2026-03-22.md)
- backlog actif: [`../TODO_ACTIVE.md`](../TODO_ACTIVE.md)
- etat livre: [`../TODO_IMPLEMENTE.md`](../TODO_IMPLEMENTE.md)
- ordre d'execution: [`EXECUTION_PLAN_2026-03-22.md`](./EXECUTION_PLAN_2026-03-22.md)
