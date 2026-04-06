# Veille runtime + eval - 21 mars 2026

Veille sourcee orientee refonte ANE. Objectif: identifier les briques reutilisables sans diluer le pipeline narratif dans un framework generique.

## Sources principales

- GOAT-Storytelling-Agent: https://github.com/GOAT-AI-lab/GOAT-Storytelling-Agent
- Prometheus-Eval: https://github.com/prometheus-eval/prometheus-eval
- DeepEval: https://github.com/confident-ai/deepeval
- LM Format Enforcer: https://github.com/noamgat/lm-format-enforcer
- Outlines: https://github.com/dottxt-ai/outlines
- llama.cpp: https://github.com/ggml-org/llama.cpp
- SCORE: https://arxiv.org/abs/2503.23512

## Ce qui ressort pour ANE

### 1. GOAT valide le pattern "plan -> scene summary -> prose"

- GOAT garde plusieurs etapes de planification avant l'ecriture scene par scene.
- Le pipeline injecte `previous_scene` dans `write_a_scene`, ce qui confirme le pattern de continuite locale deja recherche dans ANE.
- Point d'application ANE:
  - convertir la `structure` JSON en resume narratif compact avant `draft`
  - injecter le dernier scene/chapitre accepte de facon plus explicite que l'outline brut

## 2. Prometheus est le meilleur candidat court terme pour remplacer une partie du gate heuristique

- Le projet expose `absolute_grade` et `relative_grade`.
- Les rubrics sont completement pilotables par l'appelant.
- Le mode batch est annonce comme >10x plus rapide que les variantes single.
- Point d'application ANE:
  - garder les heuristiques locales comme garde-fou rapide
  - ajouter un juge secondaire `absolute_grade` pour `outline_like`, continuite, resolution, densite dramatique
  - reserver `relative_grade` au comparatif `draft_v1` vs `draft_v2`

## 3. DeepEval est pertinent pour industrialiser les tests d'eval

- DeepEval peut tourner sans integration pytest, mais s'integre aussi tres bien dans un pipeline de tests.
- Le projet montre un pattern dataset + parametrisation pytest, directement compatible avec la structure `tests/` d'ANE.
- Point d'application ANE:
  - ne pas l'utiliser comme moteur principal du gate
  - l'utiliser pour des suites d'evaluation regressives sur un corpus fixe de chapitres/smokes

## 4. LM Format Enforcer est la meilleure piste "faible friction" pour les sorties structurees

- Support explicite JSON Schema, regex, `llama.cpp`, vLLM, transformers.
- Le projet insiste sur une integration dans les pipelines existants, sans rewriter toute la boucle d'inference.
- Point d'application ANE:
  - priorite si on introduit un runtime vLLM ou un server OpenAI-compatible pilotable
  - utile pour `critique`, `gate`, `memory`
  - moins utile si ANE reste exclusivement derriere le shim Mascarade actuel qui ne propage pas encore toutes les contraintes de format

## 5. Outlines est plus ambitieux mais plus intrusif

- Outlines promet des sorties structurees garanties, directement "during generation".
- Le modele d'API est tres elegant, mais plus proche d'un substrate de generation que d'un simple add-on.
- Point d'application ANE:
  - interessant si ANE controle un runtime Python local de bout en bout
  - moins prioritaire que LM Format Enforcer pour une integration rapide sur le chemin actuel `OpenAI-compatible -> runtime`

## 6. llama.cpp confirme une contrainte strategique deja observee sur le terrain

- `llama-server` supporte les grammaires GBNF et un fichier JSON de grammaire.
- Cela confirme que le chemin `llama.cpp` doit etre traite comme un runtime de premier rang, pas juste comme contournement de secours.
- Point d'application ANE:
  - elevage de `llama.cpp` au rang de profil runtime officiel
  - exploration ulterieure de grammaires pour les etapes JSON

## 7. SCORE reste une reference conceptuelle forte pour la memoire

- Le papier formalise state tracking + episode summaries + retrieval hybride.
- Point d'application ANE:
  - ne pas copier l'architecture telle quelle
  - reutiliser ses idees pour un futur lot "memoire episode/state" sans abandonner le stockage fichier

## Priorites recommandees

1. Phase immediate
   - finir l'extraction `core/runtime/*`
   - brancher `next_lots` et les probes dessus
2. Phase eval
   - ajouter un spike Prometheus sur quelques chapitres reels
   - garder DeepEval pour les regressions offline
3. Phase structured output
   - prioriser LM Format Enforcer avant Outlines
   - explorer GBNF/grammaires via `llama.cpp` seulement si le runtime le permet proprement

## Decision de refonte

- ANE garde le pipeline narratif, le gate local et les artefacts.
- Mascarade / `llama.cpp` restent des substrates runtime.
- Les frameworks d'eval et de generation structuree doivent rester optionnels et branchables, jamais absorbés au coeur du pipeline.
