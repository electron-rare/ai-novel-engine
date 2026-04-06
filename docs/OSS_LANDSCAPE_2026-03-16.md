# Veille OSS - 16 mars 2026

Veille sur des projets et librairies open source proches ou reutilisables pour `ai-novel-engine`.

Derniere mise a jour : 16 mars 2026 (session 3 — lots baselines/priority_models/french_models termines + veille agent complementaire).

## Lecture rapide

Le besoin ANE n'est pas "adopter une plateforme agentique complete". Le besoin est:

- garder un contrat OpenAI-compatible local
- mieux piloter les runtimes et les logs
- garder une boucle d'eval/garde-fou sobre
- **faire passer `outline_like` et `truncated_ending`**

## Addendum web verifie — 17 mars 2026

Synthese issue d'une verification web directe sur les repos:

- `promptfoo/promptfoo`: MIT, ~17k stars, evals + red teaming en local et CI/CD; bon candidat pour industrialiser les campagnes de regression prompts
- `confident-ai/deepeval`: Apache-2.0, ~14k stars, metriques G-Eval et integration pytest; bon candidat pour formaliser le gate narratif en tests automatises
- `noamgat/lm-format-enforcer`: MIT, ~2k stars, contraintes regex/JSON au niveau token; pertinent pour bloquer les sorties de type outline/markdown
- `GOAT-AI-lab/GOAT-Storytelling-Agent`: MIT, ~136 stars, pattern plan -> scenes avec contexte `previous_scene`; utile pour la conversion structure -> resume narratif avant draft

Decision court terme:

1. Prioriser un POC `deepeval` sur 10 chapitres de reference
2. Tester `lm-format-enforcer` sur le chemin `llama.cpp` pour prevenir `outline_like`
3. Garder `promptfoo` pour orchestration de campagnes, pas pour remplacer le pipeline ANE

## Addendum web verifie - remote ops Mascarade (17 mars 2026)

Projets verifies pour l'idee tower/kxkm:

- `BerriAI/litellm`: gateway OpenAI-compatible multi-provider, utile comme reference de routage/observabilite centralisee
- `Autossh/autossh`: maintien automatique des tunnels SSH, bon candidat pour stabiliser `8110`/`8111`
- `fatedier/frp`: reverse proxy/NAT traversal, option si SSH direct devient fragile
- `tmux-python/tmuxp`: sessions tmux declaratives, utile pour standardiser cockpit ops
- `Textualize/textual`: framework TUI Python moderne, utile si on evolue au-dela des TUIs texte actuelles
- `getsops/sops`: gestion secrete des credentials/env en fichiers chiffres, utile pour durcir les presets

Decision court terme:

1. Prioriser `autossh` pour tenir les tunnels tower/kxkm sans intervention manuelle
2. Garder `mascarade_remote_tui.py` comme cockpit minimal immediat
3. Evaluer `litellm` seulement comme reference architecture, pas comme remplacement du pipeline ANE

## Projets a surveiller — Runtime et cockpit

| Projet | Type | Pourquoi c'est utile a ANE | Ce qu'il faut emprunter | Lien |
|---|---|---|---|---|
| `llama.cpp` | runtime local | brique la plus directe pour servir les blobs GGUF `qwen2.5` hors Ollama natif | `llama-server`, alias de modeles, healthchecks simples | [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) |
| `Open WebUI` | cockpit local LLM | reference produit pour visualiser runtimes, modeles et interactions locales | idees d'observabilite locale, pas son stack complet | [open-webui/open-webui](https://github.com/open-webui/open-webui) |
| `Promptfoo` | evals / guardrails | proche du besoin ANE de comparer des sorties et de verrouiller des regressions | patterns d'evaluations declaratives et de matrices de tests | [promptfoo/promptfoo](https://github.com/promptfoo/promptfoo) |
| `Flowise` | orchestration visuelle | utile comme source d'idees pour un futur cockpit, pas comme coeur narratif | inspiration UI / debugging de flux | [FlowiseAI/Flowise](https://github.com/FlowiseAI/Flowise) |
| `SillyTavern` | interface locale narrative | interessant pour la partie auteur/runtime local et les usages fictionnels | idees UX pour mode auteur, presets, gestion contextuelle | [SillyTavern/SillyTavern](https://github.com/SillyTavern/SillyTavern) |
| `koboldcpp` | runtime local fiction | tres proche des usages d'ecriture locale et des modeles GGUF pour narration | inspiration sur le serving local fiction-first | [LostRuins/koboldcpp](https://github.com/LostRuins/koboldcpp) |

## Projets a surveiller — Contraintes decodage (prevention outline_like)

| Projet | Facilite | Pourquoi c'est utile a ANE | Ce qu'il faut emprunter | Lien |
|---|---|---|---|---|
| `lm-format-enforcer` | **Facile** | filtre logit regex + JSON schema ; integration `llama-cpp-python` documentee ; bloque `#`, `*`, `-` au niveau token | regex `^[^#*\-]{20,}` appliquee au sampling — zero Markdown sans fine-tuning | [noamgat/lm-format-enforcer](https://github.com/noamgat/lm-format-enforcer) |
| `dottxt/outlines` | Moyen | logit masking via automates finis ; mode regex grammar ; `outlines-core` Rust pour C-bindings llama.cpp | `RegexGuide` pour bannir tokens structurants dans draft/rewrite ; si outlines-core deja installe | [dottxt-ai/outlines](https://github.com/dottxt-ai/outlines) |
| `microsoft/guidance` | Moyen | entrelace Python et generation ; `gen()` avec regex ; backend `llama_cpp` disponible | forcer des paragraphes de prose continue via grammaire | [microsoft/guidance](https://github.com/microsoft/guidance) |
| `IterGen` (ICLR 2025) | Difficile | generation liee a grammaire avec reutilisation KV-cache ; backtracking clause a clause sans regenration complete | pattern applicable a la detection prose vs liste | [arxiv:2410.07295](https://arxiv.org/abs/2410.07295) |
| `Awesome-LLM-Constrained-Decoding` | Reference | liste curatee de papiers+code sur le decodage contraint (2022-2025) | carte de navigation OSS | [Saibo-creator/Awesome-LLM-Constrained-Decoding](https://github.com/Saibo-creator/Awesome-LLM-Constrained-Decoding) |
| `FMBench` (arxiv, fev 2025) | Reference | benchmark sur la conformite de formatage de sortie (Markdown vs prose) ; SFT+RLFT reduit le Markdown sans contrainte dure | reference pour valider l'impact des prompts sur le format de sortie | [arxiv:2602.06384](https://arxiv.org/abs/2602.06384) |

## Projets a surveiller — Qualite narrative et evals

| Projet | Type | Pourquoi c'est utile a ANE | Ce qu'il faut emprunter | Lien |
|---|---|---|---|---|
| `GOAT-Storytelling-Agent` | pipeline narratif | convertit un plan structurel en resume narratif avant injection dans draft | pattern outline→summary pour eviter `outline_like` dans le modele | [malik-kb/GOAT-Storytelling-Agent](https://github.com/malik-kb/GOAT-Storytelling-Agent) |
| `story-evaluation-llm` (lars76) | evaluateur narratif | 15 criteres ; 5 categories de faiblesses dont "list-like structure" et "heading use" | remplacement potentiel du garde-fou `gate` heuristique ; taxonomie de faiblesses directement reutilisable | [lars76/story-evaluation-llm](https://github.com/lars76/story-evaluation-llm) |
| `prometheus-eval` (Prometheus 2) | LLM-as-judge | modele 7B/14B open-weight ; rubrique 1-5 personnalisable ; absolu + pairwise ; fully local | rubrique "absence de listes et titres" en francais — remplace les heuristiques fragiles | [prometheus-eval/prometheus-eval](https://github.com/prometheus-eval/prometheus-eval) |
| `EQ-bench / longform-writing-bench` | benchmark long | evalue planification, coherence, developpement personnage, qualite prose sur roman court | criteres de coherence narrative ; juge swappable vers modele local | [EQ-bench/longform-writing-bench](https://github.com/EQ-bench/longform-writing-bench) |
| `EQ-bench / creative-writing-bench` | benchmark creatif | rubrique 18 questions ; agregation multi-juge ; criteres style/voix/tension | reference pour calibrer un juge local ANE | [EQ-bench/creative-writing-bench](https://github.com/EQ-bench/creative-writing-bench) |
| `EQ-bench / Judgemark-v2` | meta-eval | evalue le juge LLM lui-meme ; fiabilite inter-evaluateurs vs baseline humain pour la fiction | valider un Prometheus local comme juge ANE | [EQ-bench/Judgemark-v2](https://github.com/EQ-bench/Judgemark-v2) |
| `dottxt/outlines` | contraintes logits | interdit des patterns Markdown au niveau du sampling — zero Markdown structurant garanti | `RegexGuide` pour bannir `#`, `*`, `-` en debut de ligne dans draft/rewrite | [dottxt-ai/outlines](https://github.com/dottxt-ai/outlines) |
| `DeepEval` | eval LLM pytest-compatible | G-Eval avec criteres personnalises, s'integre dans une suite pytest | evals de prose comme tests unitaires narratifs | [confident-ai/deepeval](https://github.com/confident-ai/deepeval) |
| `distilabel` (Argilla) | pipeline eval | orchestrateur pipeline eval + `PrometheusEval` task integree | orchestrer des runs Prometheus locaux sur les lots ANE | [argilla-io/distilabel](https://github.com/argilla-io/distilabel) |
| `WritingBench` (X-PLUG) | benchmark ecriture | 6 domaines, 100 sous-domaines ; pipeline de juge automatise ; agnostique a la langue | grille d'evaluation etendue pour les lots ANE | [X-PLUG/WritingBench](https://github.com/X-PLUG/WritingBench) |
| `story-bench` (clchinkc) | benchmark narratif | Story Theory Benchmark ; criteres narratifs theoriques ; leaderboard ; flag des sorties trop structurantes | grille theorie narrative adaptable aux lots ANE | [clchinkc/story-bench](https://github.com/clchinkc/story-bench) |
| `lechmazur/writing` | benchmark creatif | 10 elements obligatoires a incorporer ; rubrique 18 questions ; agregation multi-juge | reference pour valider la completude narrative (elements d'intention injected vs produits) | [lechmazur/writing](https://github.com/lechmazur/writing) |

## Projets a surveiller — Continuite narrative et architectures pipeline

| Projet | Type | Pourquoi c'est utile a ANE | Ce qu'il faut emprunter | Lien |
|---|---|---|---|---|
| `SCORE` (arxiv, mars 2025) | pattern RAG narratif | tracker symbolique + episodes hierarchiques + recuperation TF-IDF/cosine injectes avant generation ; +23.6% coherence, -41.8% hallucinations | **pattern direct** pour un gate de continuite avant chaque lot | [arxiv:2503.23512](https://arxiv.org/abs/2503.23512) |
| `KazKozDev/NovelGenerator` | pipeline roman Ollama-natif | multi-agents ; suivi de la connaissance personnage par timeline ; threads narratifs paralleles | structures de donnees d'etat personnage + scene ; compatible Ollama | [KazKozDev/NovelGenerator](https://github.com/KazKozDev/NovelGenerator) |
| `datacrystals/AIStoryWriter` | ecrivain roman local | Ollama-compatible ; maintient traits personnage coherents ; code Python inspectable | coherence des traits personnage chapitre a chapitre | [datacrystals/AIStoryWriter](https://github.com/datacrystals/AIStoryWriter) |
| `Awesome-Story-Generation` | reference papiers | liste curatee generation narrative LLM era (2023-2025) : planning, coherence, consistance | carte de navigation pour les prochaines iterations narratives ANE | [yingpengma/Awesome-Story-Generation](https://github.com/yingpengma/Awesome-Story-Generation) |

## Projets a surveiller — Francais et qualite de prose

| Projet | Type | Pourquoi c'est utile a ANE | Ce qu'il faut emprunter | Lien |
|---|---|---|---|---|
| `CroissantLLM` | modele bilingue FR/EN | entraine sur corpus FR/EN equilibre ; meilleur candidat comme juge de prose FR local | modele juge natif francais pour Prometheus — evite un juge anglophone | [HuggingFace blog](https://huggingface.co/blog/manu/croissant-llm-blog) |
| `FrenchBench` (Quantmetry) | benchmark FR NLP | evalutation multi-taches FR dont generation ; taches de generation de qualite | base de reference pour calibrer les evaluations FR dans ANE | [Quantmetry/FrenchBench](https://github.com/Quantmetry/FrenchBench) |
| Leaderboard Open LLM Francais | leaderboard | classe les modeles sur benchmarks FR specifiques dont generation | reference pour choisir les prochains modeles FR a tester dans ANE | [HuggingFace Leaderboard FR](https://huggingface.co/spaces/fr-gouv-coordination-ia/Leaderboard_Open_LLM_en_francais) |
| CamemBERT / CamemBERT-bio | scorer de perplexite FR | masked-LM ; perplexite comme proxy de fluidite grammaticale FR | gate de fluidite FR leger avant un juge lourd — rejette les lots avec perplexite anormale | [HuggingFace camembert-base](https://huggingface.co/almanach/camembert-base) |
| `COLE` (arxiv:2510.05046) | benchmark NLU FR | 23 taches NLU FR ; 94 modeles evalues ; variation regionale ; zero-shot QA | reference pour classer les prochains modeles candidats `french_models` avant de les tester dans ANE | [arxiv:2510.05046](https://arxiv.org/abs/2510.05046) |

## Recommandations concretes

### P0 — outline_like (immediate, effort faible)

Outil recommande : **`lm-format-enforcer` + `llama-cpp-python`**

```python
from lmformatenforcer import RegexParser
from lmformatenforcer.integrations.llamacpp import build_llamacpp_logits_processor

# Regex qui autorise uniquement des caracteres de prose
# Bloque #, *, -, > au niveau logit
parser = RegexParser(r"[A-Za-zÀ-ÿ ,\.;:!\?\"\'\(\)\n]{50,}")
logits_processor = build_llamacpp_logits_processor(llm, parser)
```

Fallback si `outlines` deja installe : utiliser `RegexGuide` avec le meme pattern.

Le papier `FMBench` (fev 2025) confirme que SFT+RLFT reduit le Markdown sans contraintes dures — voie de fine-tuning future quand les baselines sont stables.

### P1 — Gate LLM-as-judge (effort moyen)

Deployer **Prometheus 2 (7B)** localement via `llama-cpp-python` ou `ollama`. Ecrire une rubrique 5 criteres en francais :

1. Absence de listes, titres, et labels structurants
2. Qualite narrative (scene jouee, pas decrite)
3. Continuite de personnage
4. Coherence de ton et de registre
5. Densite prose (cible 600-800 mots de recit continu)

Utiliser la taxonomie de faiblesses `lars76/story-evaluation-llm` comme base de formulation. Orchestrer avec `distilabel` + tache `PrometheusEval`.

### P2 — Continuite narrative (effort moyen)

Implémenter le **pattern SCORE** (arxiv:2503.23512) :

1. Avant chaque lot, recuperer les k passages les plus pertinents des chapitres precedents via TF-IDF + cosine
2. Injecter un bloc d'etat symbolique (personnages actifs, lieux, fils narratifs ouverts)
3. Passer les deux dans le contexte de `draft_v1`

Reference d'implementation : `KazKozDev/NovelGenerator` pour les structures de donnees d'etat par timeline.

### P3 — Qualite prose FR (effort faible a proto)

Pas d'outil cle en main. Approche recommandee :

- **Court terme** : perplexite via CamemBERT comme gate leger de fluidite FR (rejette les lots >seuil)
- **Moyen terme** : Prometheus 2 + rubrique FR + CroissantLLM comme juge natif bilingue
- **Long terme** : fine-tuner un petit CroissantLLM comme scorer FR dedie, une fois assez de donnees de lots

### A moyen terme (general)

- evaluer `prometheus-eval` ou `story-evaluation-llm` comme remplacement LLM-as-judge du gate heuristique actuel
- regarder `dottxt/outlines` si les contraintes logits deviennent accessibles via llama-server (grammar-based sampling)
- regarder `Open WebUI` et `SillyTavern` si un vrai poste auteur local devient prioritaire
- tester les modeles du Leaderboard Open LLM Francais comme prochains candidats `french_models`

### A ne pas faire maintenant

- remplacer le pipeline ANE par une plateforme agentique generaliste
- noyer la logique auteuriale dans un builder de flows
- multiplier les dependances UI avant d'avoir stabilise les reruns runtime

## Fix outline_like — recette directe

D'apres l'analyse des projets GOAT, lm-format-enforcer et des patterns few-shot :

1. **Output primer** : terminer le prompt `draft_v1` par `---\n\n` suivi des premiers mots de la premiere scene (force le modele a continuer en prose, pas en titre)
2. **Few-shot BAD/GOOD** : ajouter 1 exemple court de MAUVAISE sortie (`# Scene\n- bullet`) et 1 BONNE sortie (prose continue) dans chaque prompt
3. **Word count explicite** : mentionner une cible de mots (`environ 800 mots`) plutot qu'un budget tokens
4. **Structure → narrative** : convertir la `structure` JSON en 2-3 phrases narratives (type GOAT) avant de l'injecter dans `draft_v1`
5. **Contrainte logit** : si llama-server avec `lm-format-enforcer`, appliquer regex prose en complement des prompts pour garantie hard
