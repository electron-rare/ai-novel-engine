# TODO implemente - AI Novel Engine

Snapshot append-only de ce qui est reellement livre.

Regle:
- n'ajouter ici qu'un lot termine
- ne pas y laisser de travail restant
- renvoyer vers `TODO_ACTIVE.md` pour les suites et blocages

## Deja implemente

### Lot livre - 7 mars 2026
- [x] Pipeline chapitre complet `intention -> structure -> draft -> critique -> rewrite -> validation -> memoire`
- [x] Artefacts standardises dans `structure/`, `brouillons/`, `manuscrit/`, `memoire/`
- [x] Normalisation des chapitres et detection explicite des collisions `chapitre_1` / `chapitre_01`
- [x] CLI `status`, `intention create`, `generate chapter --chapter XX` et alias `write --chapter XX`
- [x] Provider generique avec implementation OpenAI-compatible et configuration par variables d'environnement
- [x] Branchement local via `mascarade` en pointant `ANE_BASE_URL` vers `http://127.0.0.1:8100`
- [x] Budgets par etape avec `ANE_MAX_TOKENS_STRUCTURE`, `..._DRAFT`, `..._CRITIQUE`, `..._REWRITE`, `..._MEMORY`
- [x] Parsing JSON tolerant pour les etapes `critique` et `memory`
- [x] Second passage de reessai cible sur `critique` et `memory` quand la premiere reponse reste invalide
- [x] Prompts versionnes par etape dans `prompts/`
- [x] Metadonnees pipeline enrichies avec `stage_attempts`, `retry_stages`, `provider.*` et `last_status_message`
- [x] Ecriture immediate de l'etape en cours dans `meta.json` avant les appels provider pour rendre les hangs lisibles
- [x] CLI non interactive avec `--approve` et `--reject`
- [x] `status` enrichi pour les chapitres en echec et en attente
- [x] Smoke script local `scripts/smoke_local_generation.sh` branche sur la vraie CLI et avec warm-up Apple via `:8100`
- [x] Presets de smoke Apple plus conservateurs et timeout local plus large pour limiter les faux negatifs de warm-up
- [x] Runbook local ANE `docs/runbooks/LOCAL_GENERATION.md`
- [x] `docs/vision.md` et `docs/roadmap.md` remplaces par une doc exploitable
- [x] Suite unitaire `python3 -m unittest discover -s tests -v` verte sur l'etat livre

### Lot livre - 8 mars 2026
- [x] Validation locale `ollama` de bout en bout avec `ollama:qwen2.5:1.5b` via `mascarade`
- [x] Validation Apple locale de bout en bout avec `apple-coreml:qwen2.5-0.5b-instruct-onnx`
- [x] Validation Apple locale de bout en bout avec `apple-coreml:qwen3.5-4b-onnx-q4f16`
- [x] Comparatif local documente dans `docs/MODEL_COMPARISON_2026-03-08.md`
- [x] Runbook local ANE et `README` realignes sur les modeles reellement valides

### Lot livre - 8 mars 2026 (garde-fou qualite)
- [x] Nouvelle etape `gate` entre `rewrite` et la validation auteur
- [x] Type `ManuscriptGateReport` et artefact `brouillons/chapitres/chapitre_XX/gate_v1.json`
- [x] Heuristiques bloquantes locales `too_short`, `truncated_ending`, `outline_like`
- [x] Budget provider `ANE_MAX_TOKENS_GATE`
- [x] `--approve` et la promotion manuscrit ne bypassent jamais le garde-fou
- [x] `meta.json`, `status` et le smoke exposent `quality_blockers`, `gate_report`, `gate_v1` et les chapitres `quality_blocked`
- [x] Revalidation du protocole qualite:
  - `ollama:qwen2.5:1.5b` -> `quality_blocked` au garde-fou
  - `apple-coreml:qwen2.5-0.5b-instruct-onnx` -> `quality_blocked` au garde-fou
  - `apple-coreml:qwen3.5-4b-onnx-q4f16` -> `provider_failed` en `rewrite`
  - `ollama:qwen2.5:7b` -> `provider_failed` par timeout client en `draft`
- [x] Suite unitaire `python3 -m unittest discover -s tests -v` verte avec 27 tests

### Lot livre - 8 mars 2026 (durcissement prose)
- [x] Prompts `draft_v1` et `rewrite_v1` renforces pour interdire titres, puces et labels de plan visibles
- [x] Consignes explicites de prose continue, de scene jouee et de fin de phrase complete
- [x] Fix runtime cote `mascarade` avec `OLLAMA_TIMEOUT_SECONDS` configurable et timeout explicite
- [x] Rerun reel `ollama:qwen2.5:1.5b` complete a nouveau jusqu'au garde-fou (`499` mots), mais reste `quality_blocked`
- [x] Rerun reel `apple-coreml:qwen2.5-0.5b-instruct-onnx` complete jusqu'au garde-fou (`538` mots), mais reste `quality_blocked`

### Lot livre - 8 mars 2026 (repair + reruns bornes)
- [x] Boucle `repair` automatique entre `gate` et `quality_blocked`
- [x] Preservation de `draft_v2.md` et ajout des artefacts `repair_vN.md`
- [x] Budget `ANE_MAX_TOKENS_REPAIR`, limite `ANE_REPAIR_MAX_PASSES` et override `ANE_REPAIR_FALLBACK_MODEL`
- [x] `meta.json`, `status` et le smoke exposent `repair_attempts`, `repair_models`, `repair_latest` et le brouillon final candidat
- [x] Timeout provider `urllib` remonte maintenant en `ProviderError`, ce qui marque correctement `failed_stage`
- [x] Le warm-up Apple du smoke remonte maintenant un message d'erreur lisible
- [x] Le fallback `repair` n'essaie plus automatiquement un autre modele `apple-coreml` au milieu d'un meme smoke; `qwen2.5-0.5b` bascule desormais vers un fallback non-Apple
- [x] Suite unitaire etendue a 34 tests verts
- [x] Reruns reels sous preset qualite borne a `300s` par requete:
  - `ollama:qwen2.5:1.5b` -> `failed_stage=structure`
  - `apple-coreml:qwen2.5-0.5b-instruct-onnx` -> `failed_stage=rewrite`
  - `apple-coreml:qwen3.5-4b-onnx-q4f16` -> `failed_stage=rewrite`
  - `ollama:qwen2.5:7b` -> `failed_stage=rewrite`
- [x] Conclusion du cycle: la boucle `repair` est livree et preparee; le goulot courant reste `rewrite` tant que les meilleurs candidats n'ont pas ete rejoues

### Lot livre - 9 mars 2026 (automation des lots utiles)
- [x] Orchestrateur central `python3 scripts/run_next_lots.py`
- [x] Manifeste versionne `automation/next_lots.toml`
- [x] Etat de reprise local et rapports machines dans `automation/state/` et `automation/reports/`
- [x] Reutilisation des smokes existants `scripts/smoke_local_generation.sh` et `mascarade/scripts/smoke_openai_compat_ane.sh`
- [x] Synchronisation directe des plans/TODOs/readmes/runbooks dans des sections `AUTO-SYNC`
- [x] Helper `mascarade/scripts/ensure_apple_models.sh` pour verifier ou installer les trois modeles Apple requis
- [x] Helper `mascarade/scripts/prepare_runtime_step.sh` pour preparer les checkpoints semi-autos de restart/switch runtime
- [x] Attente courte sur `/models` apres un switch Apple pour eviter les faux checkpoints `aucun modele`
- [x] Couverture unitaire du manifeste, des checkpoints Apple, du rendu `AUTO-SYNC` et des helpers shell

### Lot livre - 9 mars 2026 (priority_models automatise)
- [x] Cycle reel `python3 scripts/run_next_lots.py --lot priority_models` termine jusqu'a `tracking_sync`
- [x] `apple-coreml:qwen3.5-4b-onnx-q4f16` accepte de bout en bout sous protocole `gate + repair`
- [x] `ollama:qwen2.5:7b` atteint `gate`, exerce `repair` en live sur deux passes, puis finit `quality_blocked` avec `outline_like`
- [x] Le comparatif local, les TODOs, les README et les runbooks disposent maintenant d'un premier resultat `accepted` sous protocole courant

### Lot livre - 13 mars 2026 (reprise et durcissement prose)
- [x] `tracking_sync` consolide maintenant les derniers verdicts connus par modele depuis `automation/reports/*/run.json`
- [x] Normalisation legere des sorties prose pour retirer les code fences et titres `# Chapitre` avant garde-fou
- [x] Heuristique `outline_like` renforcee pour mieux detecter headings, listes, titres et labels structurants
- [x] Prompts `draft_v1`, `rewrite_v1`, `repair_v1` et `gate_v1` resserres contre `outline_like` et `truncated_ending`
- [x] Le rerun comparable `automation/reports/apple_rerun_preset_20260313T223555Z` passe `accepted` sans `repair` et reconfirme la reference Apple locale
- [x] Etat automatise `baselines` clos proprement; `stateful-mistral7b-instruct-int4-coreml` sort du chemin critique
- [x] Suite unitaire etendue a 43 tests verts

### Lot livre - 16 mars 2026 (ops cockpit + deep docs)
- [x] Module partage `core/reporting.py` pour centraliser lecture `run.json`, tri des reports et aggregation stderr
- [x] `scripts/reports_ops.py analyze-logs` corrige pour rattacher les erreurs aux vrais modeles
- [x] `scripts/next_lots_tui.py` et `scripts/reports_ops.py` executes directement depuis `scripts/` sans casser les imports repo
- [x] Nouveau cockpit TUI `scripts/ops_tui.py`
- [x] Fix de deduplication des evenements de chronologie lors d'un rerun du meme chapitre accepte
- [x] Nouveaux documents: contexte, memoire, plan, spec systeme, feature map, carte d'agents, veille OSS
- [x] `docs/runbooks/AUTOMATION.md`, `docs/workflow.md`, `docs/dev/README.md` et `README.md` rebranches sur l'etat reel
- [x] Suite unitaire verte a `55` tests

### Lot livre - 16 mars 2026 (refonte globale — phase 1)
- [x] Memoire projet initialisee : `MEMORY.md` + 5 fichiers de memoire (user, feedback, project x3)
- [x] `docs/OSS_LANDSCAPE_2026-03-16.md` enrichi : GOAT-Storytelling-Agent, prometheus-eval, story-evaluation-llm, dottxt/outlines, DeepEval
- [x] `docs/AGENTS_2026-03-16.md` mis a jour : Agent 6 Qualite code, todos actifs par agent
- [x] `docs/FEATURE_MAP_2026-03-16.md` mis a jour : Carte 7 Qualite code, lot `french_models`
- [x] Fix 4 bare `except Exception` dans `core/next_lots.py` → `(OSError, json.JSONDecodeError, ValueError)`
- [x] Prompts `draft_v1`, `rewrite_v1`, `repair_v1` : output primer + few-shot BAD/GOOD + cible 600-800 mots
- [x] Nouveaux tests `IntentionGate` (11), `PromptStore` (7), CLI intention (3)

### Lot livre - 2 avril 2026 (normalisation des verdicts gate/judge)
- [x] `NarrativeJudgeReport` normalise maintenant ses blockers avant persistence: aliases historiques unifies, labels inconnus filtres, doublons supprimes et `ready_for_manuscript` recalcule
- [x] `ManuscriptGateReport` applique la meme normalisation sur `blockers`, `heuristic_blockers`, `judge_blockers` et recommandations
- [x] Les sorties parseables mais contradictoires des petits modeles locaux sont maintenant rendues plus coherentes pour ANE avant `_sanitize_gate_report()`
- [x] Couverture unitaire ajoutee pour les aliases historiques et la revalidation de `ready_for_manuscript`
- [x] Suite unitaire a 77 tests verts

### Lot livre - 16 mars 2026 (refonte globale — phase 2)
- [x] `_finish_stage()` extrait dans `core/generation/pipeline.py` : `generate_chapter()` allege (-12 lignes de boilerplate)
- [x] `_iter_chapters_with_status()` extrait dans `core/project/loader.py` : 3 methodes `failed/quality_blocked/awaiting_acceptance` factorisees
- [x] `Makefile` enrichi : `healthcheck`, `smoke-apple/ollama/mistral`, `lot-priority/baselines/french/full/sync`, `resume`, `test-v`
- [x] `README.md` nettoye : bloc CHANTIER stale supprime
- [x] Suite unitaire a 77 tests verts (stable apres refactors)

### Lot livre - 16 mars 2026 (refonte globale — phase 3)
- [x] `_close_json_delimiters()` robustifie dans `core/generation/models.py` : rebuild caractere par caractere, closers mal assortis repares, stray closers droppes
- [x] 3 nouveaux tests `JsonRepairTests` : mismatched closer, stray closer, truncated string in array
- [x] `docs/OSS_LANDSCAPE_2026-03-16.md` enrichi : section contraintes decodage (lm-format-enforcer, outlines-core, guidance, IterGen, FMBench), section continuite narrative (SCORE pattern, KazKozDev/NovelGenerator, AIStoryWriter), section FR (CroissantLLM, FrenchBench, leaderboard FR, CamemBERT perplexite), benchmarks creatifs EQ-bench (longform, creative, Judgemark-v2), distilabel+PrometheusEval
- [x] Recommandations P0/P1/P2/P3 structurees avec recettes concretes (lm-format-enforcer regex, Prometheus 2 rubrique FR, SCORE pattern, CamemBERT gate)
- [x] Suite unitaire a 80 tests verts

### Lot livre - 16 mars 2026 (fix outline_like — normalisation headings)
- [x] Root cause identifiee depuis lot `baselines` rejoue : `qwen2.5:1.5b` genere `### Scene N — titre` comme headings de scene, non stripes par la normalisation
- [x] `_normalize_generated_prose()` : strip ALL `#{1,6}` headings (au lieu du seul `# Chapitre`) — prevention directe de `outline_like` avant gate
- [x] `_is_outline_like()` : tightening du check `scene_heading` — ne se declenche plus sur le mot "scene" dans la prose courante, seulement sur les labels structurants (`### Scene N`, `Scene 1:`)
- [x] `NormalizeProseTests` (5 tests) : strips H1/H2/H3, prose contenant "scene" non flagee, labels structurants correctement detects
- [x] Suite unitaire a 85 tests verts

### Lot livre - 16 mars 2026 (tests CLI + reporting)
- [x] 6 nouveaux tests `CLIIntentionTests` : chapitre invalide, intention en doublon, contenu vide, `main([])` → status, `ProviderError` via generate, `ProviderError` via write
- [x] 18 nouveaux tests `ReportingHelpersTests` : safe_read_json (3), safe_stamp (3), extract_stderr (2), classification_count (2), folder_timestamp (2), latest_report_run (2), log_label (4)
- [x] Suite unitaire a 109 tests verts

### Lot livre - 16 mars 2026 (fix dense_bullet_list + validation baselines)
- [x] `_is_outline_like()` : ajout compteur `bullet_line_count`; 4+ lignes bullet = `dense_bullet_list` (marqueur solo suffisant) — models 0.5b generant des listes pures maintenant bloques correctement
- [x] 2 nouveaux tests `NormalizeProseTests` : `dense_bullet_list` (4 bullets flagges), prose avec 1 bullet non flaggee
- [x] Validation end-to-end lot `baselines` : `ollama:qwen2.5:1.5b` → `quality_blocked ['truncated_ending']` uniquement — plus d'`outline_like` (fix normalisation headings confirme)
- [x] `apple-coreml:qwen2.5-0.5b-instruct-onnx` → `quality_blocked ['truncated_ending', 'outline_like']` (dense_bullet_list detecte correctement apres repair)
- [x] Suite unitaire a 111 tests verts

### Lot livre - 16 mars 2026 (fix budgets rewrite/repair + rerun priority_models)
- [x] Diagnostic : `ANE_MAX_TOKENS_REWRITE=768` et `ANE_MAX_TOKENS_REPAIR=512` trop courts — prose refusee pour `truncated_ending` budget, pas qualite
- [x] `automation/next_lots.toml` : `ANE_MAX_TOKENS_REWRITE` 768 → 1024, `ANE_MAX_TOKENS_REPAIR` 512 → 1024
- [x] Rerun `priority_models` avec budgets 1024 : `apple-coreml:qwen3.5-4b-onnx-q4f16` → `accepted` (531 mots, gate vert)
- [x] `ollama:qwen2.5:7b` → `quality_blocked ['truncated_ending']` par LLM gate (fin narrative insuffisante, pas de decision risquee)
- [x] Lot `french_models` lance : `ollama:mistral-nemo:latest` via llama-server `:8091` (rapport `20260316T220423Z`)

### Lot livre - 16 mars 2026 (french_models — mistral-nemo)
- [x] Premier run `ollama:mistral-nemo:latest` via `llama-server` `:8091` avec budgets 1024
- [x] Gate LLM : `quality_blocked ['outline_like', 'incomplete', 'lacks_narrative_continuity']`
- [x] Prose sans headings ni bullets (fix normalisation tient) mais scene trop condensee (316 mots rewrite)
- [x] Comparatif mis a jour : `docs/MODEL_COMPARISON_2026-03-16.md`
- [x] Blockers narratifs mistral-nemo documentes — requalification apres ajustements prompts

### Lot livre - 21 mars 2026 (refonte runtime — phase 1)
- [x] Couche runtime minimale extraite sous `core/runtime/`
- [x] `core/runtime/config.py` ajoute comme premier point d'entree runtime partage
- [x] `core/runtime/policies.py` ajoute pour sortir du pipeline les regles de fallback et la contrainte Apple
- [x] `core/runtime/models.py` enrichi avec contraintes runtime explicites
- [x] `core/runtime/health.py` sait maintenant remonter la sante runtime et un catalogue de modeles OpenAI-compatible
- [x] `OpenAICompatibleProvider` delegue maintenant le transport OpenAI-compatible a `OpenAIChatRuntimeClient`
- [x] `core/generation/provider.py` utilise `OpenAICompatibleRuntimeConfig` comme source de verite de config
- [x] `core/generation/pipeline.py` delegue le fallback `repair` a `core/runtime/policies.py`
- [x] `core/next_lots.py` reutilise `runtime_probe_profile` et `runtime_model_ids`
- [x] `core/next_lots.py` recompilable a nouveau (`IndentationError` corrige)
- [x] Tests dedies ajoutes pour config / policies / health dans `tests/test_runtime_layer.py`
- [x] Suite unitaire a `128 tests` verts

### Lot livre - 21 mars 2026 (refonte runtime — phase 2)
- [x] `core/generation/provider.py` repose maintenant sur `core/runtime/config.py` pour la configuration OpenAI-compatible
- [x] `core/runtime/config.py` expose `runtime_probe_profile()`
- [x] `core/runtime/health.py` expose `runtime_model_ids()` pour mutualiser la lecture du catalogue runtime
- [x] `core/next_lots.py` consomme ces helpers partages au lieu de reconstruire localement une partie des profils runtime
- [x] `scripts/ops_tui.py` utilise la meme sonde runtime partagee pour les endpoints OpenAI-compatibles
- [x] Tests runtime enrichis dans `tests/test_runtime_layer.py`
- [x] Suite unitaire a `131 tests` verts

### Lot livre - 21 mars 2026 (refonte runtime — phase 3)
- [x] `core/runtime/checkpoints.py` extrait la decision de checkpoint manuel runtime
- [x] `core/runtime/preflight.py` extrait le preflight Ollama natif
- [x] `core/runtime/health.py` expose `current_apple_model()` et `wait_for_expected_apple_model()`
- [x] `core/next_lots.py` ne porte plus directement la logique de checkpoint Apple ni le preflight HTTP Ollama natif
- [x] Tests dedies ajoutes dans `tests/test_runtime_orchestration.py`
- [x] Suite unitaire a `138 tests` verts

### Lot livre - 21 mars 2026 (refonte runtime — phase 4)
- [x] `core/runtime/profiles.py` formalise les noms de profils runtime et de probes (`mascarade_local`, `mascarade_remote_*`, `apple_coreml_single_model`, `ollama_openai_compatible`, `llama_cpp_local`)
- [x] `core/runtime/models.py` encode explicitement le mode `response_format` dans `RuntimeCapabilities`
- [x] `core/runtime/config.py` nomme les profils a partir du registre runtime partage
- [x] `core/next_lots.py` et `scripts/ops_tui.py` consomment maintenant ce registre au lieu de coder les noms en dur
- [x] `tests/test_runtime_profiles.py` couvre le mapping des profils et des probes runtime
- [x] Suite unitaire a `140 tests` verts

### Lot livre - 21 mars 2026 (refonte runtime — phase 5)
- [x] `core/runtime/remote_hosts.py` factorise la configuration des hosts remote Mascarade
- [x] `scripts/mascarade_remote_tui.py` consomme le registre de profils runtime et affiche maintenant le profil probe + le modele actif
- [x] `scripts/setup_mascarade_launchd.py` reutilise la meme source de verite pour les hosts remote
- [x] `core/runtime/orchestration.py` extrait le plan d'execution runtime, les signaux checkpoint et le catalogue Ollama hors de `core/next_lots.py`
- [x] `core/next_lots.py` consomme maintenant ce module d'orchestration pour la strategie runtime restante
- [x] Tests dedies ajoutes dans `tests/test_mascarade_remote_tui.py` et `tests/test_runtime_execution_plan.py`
- [x] Suite unitaire a `152 tests` verts

### Lot livre - 22 mars 2026 (control plane — extraction tracking_sync)
- [x] `core/tracking_sync.py` extrait la synchronisation documentaire auto-sync hors de `core/next_lots.py`
- [x] `core/next_lots.py` est recentre sur orchestration, etat et commandes
- [x] Les tests de sync documentaire sont isoles dans `tests/test_tracking_sync.py`
- [x] Les tests d'orchestration visibles restent dans `tests/test_next_lots.py`
- [x] Suite unitaire Python ciblee relancee apres extraction

### Lot livre - 22 mars 2026 (qualite narrative — juge secondaire)
- [x] `core/evaluation/` ajoute une interface `NarrativeJudge` et son implementation `ProviderNarrativeJudge`
- [x] Activation optionnelle du juge via `ANE_JUDGE_MODEL`
- [x] Nouveau prompt `prompts/judge_narrative_v1.txt` + retry JSON strict
- [x] `ManuscriptGateReport`, `gate_v1.json` et `meta.json` exposent maintenant `judge_report` et `judge_blockers`
- [x] `_repair_focus()` traite maintenant explicitement `missing_risky_decision`, `missing_immediate_consequence`, `incomplete_scene`, `weak_narrative_continuity`
- [x] Les prompts `gate_v1`, `rewrite_v1` et `repair_v1` ont ete resserres sur decision risquee + consequence immediate
- [x] Suite unitaire Python complete relancee a `156 tests` verts

### Lot livre - 22 mars 2026 (requalification narrative + hygiene manifeste)
- [x] `llama-server` local `:8091` revalide en chargeant et servant `ollama:qwen2.5:7b`
- [x] `llama-server` local `:8091` revalide en chargeant et servant `ollama:mistral-nemo:latest`
- [x] Rerun cible `ollama:qwen2.5:7b` avec `ANE_JUDGE_MODEL=ollama:qwen2.5:7b` :
  - verdict final `quality_blocked`
  - blockers finaux `truncated_ending`, `missing_risky_decision`
  - workspace `automation/reports/20260322_qwen2_5_7b_judge`
- [x] Rerun cible `ollama:mistral-nemo:latest` avec `ANE_JUDGE_MODEL=ollama:mistral-nemo:latest` :
  - verdict final `quality_blocked`
  - blockers finaux `truncated_ending`, `missing_immediate_consequence`
  - workspace `automation/reports/20260322_mistral_nemo_judge`
- [x] `automation/next_lots.toml` repointe vers le vrai repo local Mascarade (`/Users/electron/Documents/Projets/mascarade`)
- [x] `automation/next_lots.toml` repointe le tracking ANE vers les snapshots docs du 22 mars 2026
- [x] `docs/runbooks/LOCAL_GENERATION.md` corrige les chemins d'exemple vers le repo Mascarade reel
- [x] Nouvelle continuite projet 22 mars ajoutee :
  - `docs/CONTEXTE_PROJET_2026-03-22.md`
  - `docs/MEMOIRE_REPRISE_2026-03-22.md`
  - `docs/EXECUTION_PLAN_2026-03-22.md`
  - `docs/MODEL_COMPARISON_2026-03-22.md`

### Lot livre - 22 mars 2026 (budgets comparables + prompt retouche)
- [x] `scripts/smoke_local_generation.sh` aligne ses budgets non-Apple par defaut sur le manifeste (`rewrite=1024`, `repair=1536`)
- [x] `README.md` aligne les budgets d'exemple sur le manifeste courant
- [x] Rerun comparable `ollama:qwen2.5:7b` avec budgets manifeste :
  - workspace `automation/reports/20260322_qwen2_5_7b_judge_budgeted`
  - verdict `quality_blocked ['truncated_ending', 'missing_risky_decision', 'incomplete_scene']`
- [x] Rerun comparable `ollama:mistral-nemo:latest` avec budgets manifeste :
  - workspace `automation/reports/20260322_mistral_nemo_judge_budgeted`
  - verdict `quality_blocked ['truncated_ending']`
- [x] Retouche courte des prompts `rewrite_v1` / `repair_v1` sur fermeture de scene, non-repetition et structure de fin
- [x] Rerun prompté `ollama:qwen2.5:7b` :
  - workspace `automation/reports/20260322_qwen2_5_7b_judge_prompted`
  - gain partiel: disparition de `incomplete_scene`, reste `quality_blocked ['truncated_ending', 'missing_risky_decision']`
- [x] Rerun prompté `ollama:mistral-nemo:latest` :
  - workspace `automation/reports/20260322_mistral_nemo_judge_prompted`
  - regression : `quality_blocked ['outline_like', 'missing_immediate_consequence']`

### Lot livre - 22 mars 2026 (gate sanitize + micro-decision qwen)
- [x] `pipeline._sanitize_gate_report()` retire maintenant `outline_like` du gate principal quand le brouillon ne declenche aucun marqueur visuel local de plan
- [x] `prompts/gate_v1.txt` force explicitement le gate LLM a preferer un diagnostic de prose faible plutot qu'un faux `outline_like` sans titres, puces ou labels visibles
- [x] `tests/test_generation_pipeline.py` couvre la sanitization `outline_like` et le nouveau guidage `_repair_focus()` sur le cout observable de la decision
- [x] `prompts/rewrite_v1.txt` et `prompts/repair_v1.txt` imposent maintenant que la decision finale soit prise et executee tout de suite, pas seulement annoncee
- [x] Rerun gatefix `ollama:mistral-nemo:latest` :
  - workspace `automation/reports/20260322_mistral_nemo_judge_gatefix`
  - faux `outline_like` supprime
  - verdict final `quality_blocked ['missing_immediate_consequence']`
- [x] Rerun gatefix `ollama:qwen2.5:7b` :
  - workspace `automation/reports/20260322_qwen2_5_7b_judge_gatefix`
  - `missing_risky_decision` supprime
  - verdict final `quality_blocked ['missing_immediate_consequence']`

### Lot livre - 22 mars 2026 (consequence immediate observable)
- [x] `prompts/rewrite_v1.txt` et `prompts/repair_v1.txt` imposent maintenant une consequence immediate dans le meme lieu et la meme minute, avec effet visible
- [x] `_repair_focus()` ajoute des exemples concrets de consequence observable et interdit explicitement de finir sur un simple depart vers la suite
- [x] Tests pipeline cibles relances pour la nouvelle guidance `missing_immediate_consequence`
- [x] Rerun consequencefix `ollama:qwen2.5:7b` :
  - workspace `automation/reports/20260322_qwen2_5_7b_judge_consequencefix`
  - verdict final `accepted`
  - aucun repair necessaire
- [x] Rerun consequencefix `ollama:mistral-nemo:latest` :
  - workspace `automation/reports/20260322_mistral_nemo_judge_consequencefix`
  - regression : `quality_blocked ['truncated_ending', 'missing_risky_decision', 'missing_immediate_consequence']`

### Lot livre - 25 mars 2026 (revalidation Mascarade local + diagnostics runtime app)
- [x] `Mascarade local_server` expose maintenant un `provider_status` honnete sur `health`, `providers/status` et `v1/providers/status`
- [x] Les providers non autorises (`Mistral`, `OpenAI` sur cette machine) ne sont plus annonces comme disponibles; ils remontent maintenant `unauthorized`
- [x] `Claude` est revalide en bout-en-bout sur `:8100/v1/chat/completions` et `:3100/api/v1/chat/completions` avec `claude:claude-sonnet-4-6`
- [x] `Mascarade API` `:3100` est revalidee sur `health`, `v1/api/models` et `v1/api/agents/catalog` contre le core local
- [x] `app_AI-novel-engine` affiche maintenant `provider_status` dans `Generation` et choisit dynamiquement le premier modele reellement actif pour son preset recommande Mascarade

## Actif
- [x] Aucun suivi actif ici. Voir `TODO_ACTIVE.md`.

## Bloque
- [x] Aucun blocage suivi ici. Voir `TODO_ACTIVE.md`.

## Prochain ordre
- [x] Mettre a jour ce fichier uniquement quand un nouveau lot est reellement termine.

## Auto-sync
<!-- AUTO-SYNC:ANE-TODO-DONE:START -->
- orchestrateur `scripts/run_next_lots.py` disponible
- manifeste `automation/next_lots.toml` charge
- derniers fichiers de suivi synchronisables via marqueurs `AUTO-SYNC`
- dernier cycle automatise observe: 2026-03-23T21:34:05+00:00
<!-- AUTO-SYNC:ANE-TODO-DONE:END -->
