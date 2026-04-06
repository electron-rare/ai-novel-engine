# Veille OSS approfondie — ai-novel-engine — 16 mars 2026

Recherche effectuée le 16 mars 2026. Sources : GitHub, arXiv, documentation officielle des projets.

---

## 1. Pipelines de génération de romans / fiction avec LLM

### 1.1 GOAT-Storytelling-Agent
- **URL** : https://github.com/GOAT-AI-lab/GOAT-Storytelling-Agent
- **Étoiles** : 136
- **Licence** : MIT
- **Pipeline** : 5 étapes de planification (init spec → enrich spec → plot structure → refine chapter outlines → scene breakdown), puis génération scène par scène. Chaque appel `write_a_scene` reçoit la scène précédente en contexte.
- **Format de scène structuré** : Characters, Place, Time, Event, Conflict, Story value, Story value charge, Mood, Outcome. Ce séparateur planning/prose évite la fuite de structure dans l'output.
- **Backend local** : supporte `llama.cpp` via `backend_uri = 'http://localhost:8080'` et HuggingFace TGI. Extensible à tout moteur OpenAI-compatible.
- **Réutilisable pour ANE** :
  - Pattern de passage `previous_scene` pour maintenir la continuité sans rechargement d'un long contexte.
  - Structure de scène normalisée utilisable comme contexte d'injection avant generation (comparable aux lorebooks).
  - Mécanisme de séparation explicite entre outline interne (non sorti) et prose générée.

### 1.2 AIStoryWriter
- **URL** : https://github.com/datacrystals/AIStoryWriter
- **Étoiles** : 220
- **Licence** : AGPL-3.0
- **Pipeline** : outline global → outline chapitres → rédaction chapitre → révision. Supporte Ollama, Google, OpenRouter avec mélange de modèles par étape.
- **Fichier `Evaluate.py`** : évaluation structurée des sorties (critères non publiés en détail dans le README).
- **Réutilisable pour ANE** :
  - Couche d'abstraction multi-provider (`Writer/Prompts.py`) avec prompts séparés par étape.
  - Inspiration pour mixer modèles locaux selon l'étape (draft léger, critique plus puissant).
  - Attention : licence AGPL-3.0 impose de publier les modifications si distribué en service réseau.

### 1.3 NovelGenerator (KazKozDev)
- **URL** : https://github.com/KazKozDev/NovelGenerator
- **Étoiles** : ~100
- **Licence** : non spécifiée dans le README (à vérifier dans le fichier LICENSE)
- **Pipeline** : génération multi-thread narrative, suivi de perspectives personnage par timeline, synchronisation des arcs parallèles.
- **Codebase** : TypeScript / React (pas Python). Composants modulaires : Components, Constants, Hooks, Services, Utilities.
- **Réutilisable pour ANE** : architecture conceptuelle de tracking d'état narratif multi-fil. Pas directement réutilisable en Python mais les patterns de cohérence sont transposables.

### 1.4 Novel-OS (mrigankad)
- **URL** : https://github.com/mrigankad/Novel-OS
- **Étoiles** : 1
- **Licence** : MIT
- **Pipeline 5 agents** :
  1. The Architect (planification 3 actes, arcs chapitre)
  2. The Scribe (prose en deep POV)
  3. The Editor (5 modes : line, developmental, pacing, dialogue, tension)
  4. The Continuity Guardian (analyse forensique : personnage / timeline / monde / plot)
  5. The Style Curator (maintien de la voix sur 300+ pages)
- **Mémoire** : `StoryState` JSON persistant (`outputs/state/story_state.json`) comme source de vérité unique.
- **Continuity Guardian output** : `CONTINUITY_REPORT` avec statuts PASS / WARNING / FAIL.
- **Réutilisable pour ANE** : structure de rapport de continuité directement applicable comme pattern de gate qualité. La décomposition en 5 rôles éditoriaux distincts est proche de l'architecture ANE (pipeline → critique → gate → repair).

### 1.5 Novel-Writer (curvedinf)
- **URL** : https://github.com/curvedinf/novel-writer
- **Étoiles** : 46
- **Licence** : MIT
- **Pipeline** : `python outline.py` pour démarrer, approche tiered (modèle gratuit pour init, modèle fort pour prose finale).
- **Réutilisable pour ANE** : peu. Sert de référence conceptuelle sur le choix de modèle par étape.

### 1.6 Book-OS / Novel-OS (forsonny)
- **URL** : https://github.com/forsonny/book-os
- **Étoiles** : non communiqué
- **Licence** : non précisée
- **Description** : workflow system avec 3 couches de contexte (Standards, Novel, Manuscripts) pour maintenir la voix de l'auteur. Compatible Claude Code, Cursor, et tout outil IA.
- **Réutilisable pour ANE** : idée des couches de contexte hiérarchiques (style sheet globale → paramètres du roman → manuscrit en cours). Applicable à la mémoire ANE.

### 1.7 RecurrentGPT
- **URL** : https://github.com/aiwaves-cn/RecurrentGPT
- **Étoiles** : 1 003
- **Licence** : non précisée (à vérifier)
- **Concept** : simulacre LLM du mécanisme LSTM. À chaque timestep : génération d'un paragraphe + mise à jour d'une mémoire court terme (prompt) et long terme (disque). Génération de longueur arbitraire.
- **Réutilisable pour ANE** :
  - Pattern de mémoire double (court terme in-prompt / long terme sur disque) directement transposable au système de mémoire ANE.
  - Gestion interactive : propose plusieurs continuations possibles pour validation auteur.

---

## 2. Benchmarks d'évaluation qualité prose / fiction

### 2.1 EQ-Bench Creative Writing Benchmark
- **URL** : https://github.com/EQ-bench/creative-writing-bench
- **Site** : https://eqbench.com/creative_writing.html
- **Étoiles** : 97
- **Licence** : non précisée
- **Philosophie** : exposer les faiblesses des modèles, pas aider à produire le meilleur output. 32 prompts difficiles × 3 itérations, scoring Elo.
- **Failure modes ciblés** : verbosité excessive, incohérence poétique, biais de longueur, biais de position dans le jugement comparatif.
- **Réutilisable pour ANE** : les 32 prompts et la grille de scoring par rubric constituent une base pour définir les critères du gate ANE. Le mécanisme d'Elo normalisé sur des modèles de référence est applicable à une évaluation comparative draft/rewrite.

### 2.2 LLM Creative Story-Writing Benchmark (lechmazur/writing)
- **URL** : https://github.com/lechmazur/writing
- **Étoiles** : 354
- **Licence** : non précisée
- **Rubrique 18 questions** :
  - Craft & Coherence (Q1–Q8) : character depth, plot structure, world building, story impact, originality, thematic cohesion, voice/POV, line-level prose quality.
  - Element Integration (Q9A–Q9J) : 10 éléments obligatoires à intégrer organiquement.
- **Scoring** : power mean (Hölder p=0.5), pondération 60/40 craft vs intégration, 7 LLMs juges indépendants.
- **Réutilisable pour ANE** : la rubrique 8 questions de craft est directement applicable comme grille de scoring du gate. Critère `outline_like` absent explicitement → peut être ajouté comme Q8bis (structure non narrative dans le texte).

### 2.3 WritingBench (X-PLUG/Alibaba)
- **URL** : https://github.com/X-PLUG/WritingBench
- **Étoiles** : 165
- **Licence** : Apache-2.0
- **Approche** : 1 000 queries réelles sur 6 domaines (créatif, persuasif, informatif, technique) × 100 sous-domaines (dont Novel Outline, Prose, Screenplay, Fan Fiction). Chaque query génère 5 critères d'évaluation spécifiques dynamiquement.
- **Modèle critique** : Qwen-7B fine-tuné disponible sur HuggingFace, déployable localement.
- **Réutilisable pour ANE** : le modèle critique Qwen-7B est une alternative locale à un LLM-as-judge cloud. La génération dynamique de critères par query est un pattern applicable à la critique adaptative (critères différents selon le type de scène).

### 2.4 story-evaluation-llm (lars76)
- **URL** : https://github.com/lars76/story-evaluation-llm
- **Étoiles** : 3
- **Licence** : MIT
- **Dataset** : 8 520 histoires × 15 modèles × 4 températures, scores moyennés.
- **15 critères narratifs** (directement réutilisables) :
  1. Grammar, spelling, punctuation quality
  2. Clarity and understandability
  3. Logical connection between events and ideas
  4. Scene construction and purpose
  5. Internal consistency
  6. Character consistency
  7. Character motivation coherence
  8. Sentence pattern variety
  9. Avoidance of clichés
  10. Natural dialogue
  11. Avoidance of predictable narrative tropes
  12. Character depth and dimensionality
  13. Realistic character interactions
  14. Ability to hold reader interest
  15. Satisfying plot resolution
- **Réutilisable pour ANE** : cette liste de 15 critères est la grille la plus directement applicable pour remplacer l'heuristique actuelle du gate. Critère 3 (logical connection) couvre outline_like partiel. À compléter avec "absence de structure non narrative dans le texte" (critère custom).

---

## 3. Frameworks LLM-as-Judge pour la prose narrative

### 3.1 Prometheus-Eval
- **URL** : https://github.com/prometheus-eval/prometheus-eval
- **Étoiles** : 1 100
- **Licence** : Apache-2.0
- **Modèles** : prometheus-7b-v2.0 et prometheus-8x7b-v2.0, fine-tunés pour l'évaluation sur rubrique personnalisée.
- **API Python** :
  ```python
  from prometheus_eval.vllm import VLLM
  from prometheus_eval import PrometheusEval
  model = VLLM(model="prometheus-eval/prometheus-7b-v2.0")
  judge = PrometheusEval(model=model)
  # absolute_grade() retourne feedback + score 1-5
  ```
- **Format rubrique** : 5 niveaux (score1_description … score5_description) sur critère custom.
- **Déploiement local** : via llamafile (quantifié 5-bit, ~12 GB RAM) ou vLLM. Serveur Flask OpenAI-compatible sur port 8081.
- **Réutilisable pour ANE** : remplacement direct de l'heuristique gate par un judge local. Définir une rubrique 1-5 sur "absence de structure non narrative" + "cohérence narrative" + "qualité prose". Batch evaluation 10× plus rapide que single.

### 3.2 DeepEval (confident-ai)
- **URL** : https://github.com/confident-ai/deepeval
- **Étoiles** : 14 100
- **Licence** : open source (fichier LICENSE.md dans le repo)
- **G-Eval** : LLM-as-judge sur critères personnalisés avec chain-of-thought, précision humaine déclarée.
- **Local LLM support** : métriques tournent localement, pas de dépendance API externe obligatoire.
- **Réutilisable pour ANE** : G-Eval + critères custom prose = gate qualité configurable en quelques lignes. Intégration dans les tests existants (`tests/test_generation_pipeline.py`).

### 3.3 JudgeLM (BAAI)
- **URL** : https://github.com/baaivision/JudgeLM
- **Étoiles** : non relevé précisément (ICLR 2025 Spotlight)
- **Licence** : open source
- **Performance** : accord > 90% avec jugement humain-humain en open-ended scenarios.
- **Réutilisable pour ANE** : alternative à Prometheus pour le jugement comparatif (draft vs rewrite).

### 3.4 quotient-ai/judges
- **URL** : https://github.com/quotient-ai/judges
- **Étoiles** : non relevé
- **Licence** : open source
- **Description** : bibliothèque légère de juges LLM basés sur la recherche, utilisables off-the-shelf.
- **Réutilisable pour ANE** : surface d'API minimale, bonne option si DeepEval est trop lourd.

---

## 4. Frameworks de cohérence narrative (mémoire / état)

### 4.1 SCORE (Story Coherence and Retrieval Enhancement)
- **Référence** : https://arxiv.org/html/2503.23512v1
- **Pas de repo GitHub autonome** (article de mars 2026)
- **Architecture** :
  - Dynamic State Tracking : suivi symbolic des états actifs/perdus/détruits des objets et personnages.
  - Context-Aware Summarization : résumés hiérarchiques par épisode (plot points, actions, progression émotionnelle).
  - Hybrid Retrieval : TF-IDF + cosine similarity FAISS + sentiment scoring.
  - Formule kernel : `K(ec,ep) = exp((S − γ|σ_diff|) / τ)`.
- **Réutilisable pour ANE** : le schéma de représentation d'état épisodique (active/lost/destroyed) est directement applicable à la mémoire ANE. Le RAG hybride TF-IDF + semantic est un upgrade du système mémoire actuel.

### 4.2 SillyTavern Memory Stack
- **SillyTavern-MemoryBooks** : https://github.com/aikohanasaki/SillyTavern-MemoryBooks — génération JSON de souvenirs scènes → lorebook vectorisé.
- **Timeline Memory** : https://github.com/unkarelian/timeline-memory — timeline de chapitres résumés, injection context intelligente sans édition manuelle.
- **TunnelVision** : https://github.com/Coneja-Chibi/TunnelVision — memory management toolkit déclaré comme tool calls (le LLM décide quand l'utiliser).
- **SillyTavern-LorebookOrdering** : https://github.com/aikohanasaki/SillyTavern-LorebookOrdering — priorité et budget d'activation des lorebooks.
- **Réutilisable pour ANE** : les patterns d'injection dynamique de contexte narratif (keyword-triggered, budget-controlled) sont transposables à la mémoire ANE sans adopter SillyTavern. Le concept de "lorebook budgeté" = injection mémoire avec limite de tokens.

### 4.3 Awesome-Story-Generation (yingpengma)
- **URL** : https://github.com/yingpengma/Awesome-Story-Generation
- **Étoiles** : 592
- **Papiers clés** :
  - RecurrentGPT (2023) : mémoire double court/long terme.
  - FACTTRACK NAACL-2025 : time-aware world state tracking dans les outlines.
  - MLD-EA (2024) : validation de cohérence émotionnelle et d'action.
  - Weaver (2024) : foundation models optimisés pour l'écriture.
  - Small LMs can outperform humans (COLING-2025) : viabilité des petits modèles pour la fiction.

---

## 5. Solutions techniques au problème outline_like / structure dans les outputs

### 5.1 Diagnostic du problème

Le problème `outline_like` / `truncated_ending` / structure dans le texte généré est un **failure mode documenté** dans plusieurs projets. Il survient quand :
1. Le modèle confond la phase de planification avec la phase de rédaction.
2. Le contexte inclut encore des éléments de l'outline au moment du draft.
3. Le modèle coupe sa génération avant la fin naturelle (budget token sous-estimé).

### 5.2 Solutions de prompting (classées par efficacité documentée)

**Technique 1 — Séparation stricte des phases (pattern GOAT)**
Ne jamais inclure l'outline brut dans le prompt de génération prose. Convertir l'outline en un bloc de contexte narratif neutre (description de la scène en prose condensée, pas en liste).

**Technique 2 — Output primer**
Terminer le prompt utilisateur avec le début de la prose souhaitée :
```
[fin du prompt système]
[début de la réponse attendue] : "Le soleil se couchait sur..."
```
Le modèle continue dans le registre amorcé. Efficace pour éviter l'émission de headers Markdown.

**Technique 3 — Few-shot avec contre-exemple explicite**
Fournir un exemple de mauvaise sortie (avec headers/liste) labelisé "MAUVAIS" et un exemple de bonne sortie labelisé "BON". Les modèles locaux répondent mieux à la démonstration qu'à l'instruction négative seule ("ne pas utiliser de headers").

**Technique 4 — Chained prompting séquentiel**
Diviser la génération d'un chapitre en N appels (une scène par appel), chacun recevant uniquement : résumé de la scène + fin de la scène précédente. Empêche la confusion planning/prose sur les contextes longs.

**Technique 5 — dottxt/outlines pour contraintes de format**
- **URL** : https://github.com/dottxt-ai/outlines
- **Étoiles** : non relevé précisément (projet .txt, très actif)
- **Licence** : Apache-2.0
- **Principe** : génération contrainte par grammaire EBNF ou regex au niveau logits. Peut forcer l'absence de certains patterns (headers Markdown `##`, listes `- `) pendant la génération.
- **Réutilisable pour ANE** : post-processing ou contrainte de génération pour interdire `\n##`, `\n-`, `\n*`, `\nCHAPITRE`, etc. Compatible Ollama/vLLM/llama.cpp via serveur.

**Technique 6 — Token budget planning**
Estimer le nombre de tokens attendus pour la scène, injecter l'instruction dans le prompt (`"Cette scène doit faire environ 800 mots. Écris la scène complète jusqu'à sa conclusion naturelle."`). Réduit les `truncated_ending` par prise de conscience du modèle sur sa progression.

### 5.3 Post-processing détection outline_like

Heuristiques robustes à implémenter :
- Ratio lignes débutant par `#`, `-`, `*`, chiffre + `.` > seuil → flag `outline_like`.
- Présence de tokens structurants : `CHAPITRE`, `SCÈNE`, `ACTE`, `---`, `===` en début de ligne.
- Longueur de la dernière phrase < 10 tokens → flag `truncated_ending`.
- Entropie des longueurs de phrases : faible entropie (toutes les phrases courtes identiques) → flag `listing_pattern`.

---

## 6. Mistral NeMo 12B — Best practices pour le français littéraire

### 6.1 Modèle

- **Modèle officiel** : `mistralai/Mistral-Nemo-Instruct-2407` (Mistral AI)
- **Variante NVIDIA** : `nvidia/Mistral-NeMo-12B-Instruct`
- **Documentation** : https://docs.mistral.ai/models/mistral-nemo-12b-24-07
- **Format prompt** : `[INST]...[/INST]` (Mistral Instruct) ou ChatML standard.
- **Contexte** : 128k tokens (tokenizer Tekken, meilleure gestion du français que SentencePiece standard).
- **Points forts** : français natif de premier rang parmi les 12B locaux, créatif, contexte long.

### 6.2 Pratiques documentées pour la fiction en français

1. **System prompt en français** : le modèle répond mieux quand la langue de la consigne correspond à la langue de génération.
2. **Éviter les instructions en anglais dans un prompt français** : crée un biais de basculement de langue partiel.
3. **Température** : 0.7–0.9 pour la prose littéraire, 0.4–0.6 pour la critique/évaluation.
4. **Top-p** : 0.9–0.95 pour la prose (évite les répétitions à basse température).
5. **Repeat penalty** : 1.1–1.15 pour éviter les boucles lexicales sur les textes longs.
6. **Format instruct ChatML** : préférer le format natif Mistral `[INST]` pour les modèles GGUF via llama.cpp. ChatML peut causer des dérives sur certaines quant.
7. **NemoMix-Unleashed-12B** : fine-tune communautaire orienté roleplay/créatif (`marinaraspaghetti/NemoMix-Unleashed-12B`) — à évaluer si le modèle de base montre des limites de registre.

### 6.3 Ressources

- Prompting guide officiel : https://docs.mistral.ai/guides/prompting_capabilities
- Modèle GGUF sur Ollama : `ollama pull mistral-nemo:12b-instruct-2407-q8_0`
- Leaderboard créatif 2026 : https://eqbench.com/creative_writing.html (Mistral NeMo se positionne dans le tier intermédiaire sur l'EQ-Bench)

---

## 7. Tableau de synthèse — Réutilisabilité immédiate pour ANE

| Priorité | Projet / Outil | Action recommandée | Impact sur ANE |
|---|---|---|---|
| P0 | `lars76/story-evaluation-llm` (15 critères) | Adopter la grille de 15 critères comme base du gate, remplacer l'heuristique actuelle | Résout outline_like, truncated_ending de façon structurée |
| P0 | `prometheus-eval/prometheus-eval` | Intégrer Prometheus-7B local comme LLM-as-judge dans le gate | Gate qualitatif reproductible, rubrique customisable |
| P1 | Pattern GOAT (séparation planning/prose) | Ne jamais passer l'outline brut au prompt draft. Convertir en résumé narratif neutre | Réduit outline_like à la source |
| P1 | Output primer technique | Amorcer le prompt de génération avec le début de la phrase | Réduit truncated_ending et structure Markdown |
| P1 | `confident-ai/deepeval` G-Eval | Wrapper les critères narratifs dans des G-Eval metrics, intégration pytest | CI/CD qualité narrative dans tests/test_generation_pipeline.py |
| P2 | SCORE état épisodique | Implémenter un state tracker (active/lost/destroyed) dans la mémoire ANE | Cohérence narrative long terme |
| P2 | RecurrentGPT mémoire double | Pattern mémoire court terme (prompt) + long terme (fichier) dans core/memory | Génération arbitrairement longue sans drift |
| P2 | Novel-OS Continuity Guardian | Ajouter un agent "guardian" post-draft qui produit un CONTINUITY_REPORT | Gate enrichi au-delà de la qualité stylistique |
| P3 | `dottxt/outlines` contraintes logits | Interdire les patterns Markdown en génération si le runtime le supporte | Correction outline_like au niveau token |
| P3 | `X-PLUG/WritingBench` critère model | Déployer le modèle critique Qwen-7B local pour scoring multi-critères | Alternative au LLM-as-judge full-size |
| P3 | Token budget planning | Injecter estimation de longueur dans le prompt draft | Réduit truncated_ending |

---

## 8. Projets à ne pas adopter (raisons)

| Projet | Raison d'exclusion |
|---|---|
| `KazKozDev/NovelGenerator` | TypeScript/React, pas Python. Architecture non portable directement. |
| `datacrystals/AIStoryWriter` | AGPL-3.0 : contrainte de publication si distribué en service. Architecture moins modulaire qu'ANE. |
| `SillyTavern` complet | UI orientée chat roleplay, pas pipeline batch. Adopter les patterns, pas le système. |
| LangChain / LangGraph complets | Overhead architectural disproportionné. ANE n'a pas besoin d'orchestration générale. |

---

## Sources

- [GOAT-Storytelling-Agent](https://github.com/GOAT-AI-lab/GOAT-Storytelling-Agent)
- [AIStoryWriter](https://github.com/datacrystals/AIStoryWriter)
- [NovelGenerator](https://github.com/KazKozDev/NovelGenerator)
- [Novel-OS (mrigankad)](https://github.com/mrigankad/Novel-OS)
- [Novel-Writer (curvedinf)](https://github.com/curvedinf/novel-writer)
- [Book-OS (forsonny)](https://github.com/forsonny/book-os)
- [RecurrentGPT](https://github.com/aiwaves-cn/RecurrentGPT)
- [EQ-Bench Creative Writing](https://github.com/EQ-bench/creative-writing-bench)
- [lechmazur/writing benchmark](https://github.com/lechmazur/writing)
- [WritingBench (X-PLUG)](https://github.com/X-PLUG/WritingBench)
- [story-evaluation-llm (lars76)](https://github.com/lars76/story-evaluation-llm)
- [prometheus-eval](https://github.com/prometheus-eval/prometheus-eval)
- [DeepEval (confident-ai)](https://github.com/confident-ai/deepeval)
- [JudgeLM (BAAI)](https://github.com/baaivision/JudgeLM)
- [quotient-ai/judges](https://github.com/quotient-ai/judges)
- [dottxt-ai/outlines](https://github.com/dottxt-ai/outlines)
- [Awesome-Story-Generation](https://github.com/yingpengma/Awesome-Story-Generation)
- [SillyTavern-MemoryBooks](https://github.com/aikohanasaki/SillyTavern-MemoryBooks)
- [Timeline Memory](https://github.com/unkarelian/timeline-memory)
- [TunnelVision](https://github.com/Coneja-Chibi/TunnelVision)
- [KoboldCpp](https://github.com/LostRuins/koboldcpp)
- [SCORE framework (arXiv 2503.23512)](https://arxiv.org/html/2503.23512v1)
- [Mozilla AI — Local LLM-as-judge avec Prometheus](https://blog.mozilla.ai/local-llm-as-judge-evaluation-with-lm-buddy-prometheus-and-llamafile/)
- [Mistral Nemo documentation](https://docs.mistral.ai/models/mistral-nemo-12b-24-07)
- [EQ-Bench leaderboard créatif](https://eqbench.com/creative_writing.html)
- [Awesome-LLM-as-a-judge](https://github.com/llm-as-a-judge/Awesome-LLM-as-a-judge)
