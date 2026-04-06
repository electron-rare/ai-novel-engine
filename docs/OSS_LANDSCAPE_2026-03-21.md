# OSS Landscape - 21 mars 2026

Veille sourcee orientee refonte d'ANE. Le but est de reperer ce qui peut etre repris comme idee, pas d'importer ces projets tels quels.

## Recommandations directes

### P0 - Contraindre les sorties structurees cote runtime

- [`lm-format-enforcer`](https://github.com/noamgat/lm-format-enforcer)
  - utile pour imposer du JSON ou des regex sans rewriter tout le pipeline
  - bon candidat si ANE veut durcir `critique` / `gate` / `memory` sur des runtimes compatibles
  - a traiter comme experience ciblee, pas comme dependance centrale

### P1 - Evaluer la prose avec un cadre de tests

- [`DeepEval`](https://github.com/confident-ai/deepeval)
  - utile comme harness d'evals Python/pytest pour comparer prompts, budgets et modeles
  - peut completer les heuristiques ANE sans les remplacer d'un coup

### P1 - Utiliser un benchmark d'ecriture comme source de criteres

- [`WritingBench`](https://github.com/X-PLUG/WritingBench)
  - benchmark recent de generation d'ecriture
  - utile pour deriver une grille d'evaluation et des criteres plus stables que les seuls heuristiques maison

## Recommandations architecture / ops

### P1 - Consolider le backend local de secours

- [`llama.cpp`](https://github.com/ggerganov/llama.cpp)
  - ANE l'utilise deja indirectement via `llama-server`
  - confirme comme substrate local robuste pour le fallback `ollama:*` quand Ollama natif casse

### P2 - Reference de gateway / abstraction provider

- [`LiteLLM`](https://github.com/BerriAI/litellm)
  - interessant comme reference de design pour les profils runtime et l'abstraction provider
  - a etudier pour les concepts, pas a adopter tel quel dans ANE

### P2 - Reference de cockpit runtime

- [Open WebUI](https://docs.openwebui.com/)
  - utile comme reference produit pour ce qui releve du cockpit et de l'operabilite locale
  - non cible comme dependance directe: ANE a besoin d'un control plane plus petit et plus TUI-first

## Recommandations plus lourdes ou a garder sous surveillance

- [`Outlines`](https://github.com/dottxt-ai/outlines)
  - tres interessant pour la generation structuree, mais integration plus structurante et plus lourde
  - a garder en lot ulterieur si `lm-format-enforcer` ne suffit pas

## Traduction concrete pour ANE

1. Garder `llama.cpp` comme backend de secours de premier rang.
2. Introduire des capacites runtime explicites avant toute nouvelle salve de tuning prompt.
3. Tester `lm-format-enforcer` sur les etapes JSON seulement.
4. Ajouter un harness d'evals type `DeepEval` ou une grille inspiree de `WritingBench`.
5. Ne pas absorber `LiteLLM` ni `Open WebUI`; ne reprendre que leurs idees de surface.
