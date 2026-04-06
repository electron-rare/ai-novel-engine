# TODO actif - AI Novel Engine

Backlog courant pour reprendre `ai-novel-engine` sans melanger le reste avec les lots deja livres.

References:

- contexte courant: [`docs/CONTEXTE_PROJET_2026-03-22.md`](./docs/CONTEXTE_PROJET_2026-03-22.md)
- memoire de reprise: [`docs/MEMOIRE_REPRISE_2026-03-22.md`](./docs/MEMOIRE_REPRISE_2026-03-22.md)
- plan courant: [`docs/EXECUTION_PLAN_2026-03-22.md`](./docs/EXECUTION_PLAN_2026-03-22.md)
- lots livres: [`TODO_IMPLEMENTE.md`](./TODO_IMPLEMENTE.md)
- spec systeme: [`docs/SYSTEM_SPEC_2026-03-21.md`](./docs/SYSTEM_SPEC_2026-03-21.md)
- agents et sous-agents: [`docs/AGENTS_2026-03-21.md`](./docs/AGENTS_2026-03-21.md)

## Memoire de reprise

- reference locale mise a jour le 2026-03-23: `apple-coreml:qwen3-4b-instruct-2507-q4f16` (3x plus rapide que l'ancienne ref)
- ancienne reference locale: `apple-coreml:qwen3.5-4b-onnx-q4f16` (remplacee)
- reference cloud: `mistral:mistral-large-latest` (via Mascarade Batch API, pas de modele en RAM)
- Mascarade routing: tout passe par `:8100` — Mistral API, Apple CoreML, Ollama P2P
- premier candidat Ollama maintenant accepte: `ollama:qwen2.5:7b`
- preuve cle du 16 mars: `ollama:qwen2.5:1.5b` a deja atteint `gate` via `llama.cpp` / `llama-server`
- juge narratif secondaire livre sous `core/evaluation/`, activable par `ANE_JUDGE_MODEL`
- rerun juge du 22 mars:
  - `ollama:qwen2.5:7b` -> `quality_blocked ['truncated_ending', 'missing_risky_decision']`
  - `ollama:mistral-nemo:latest` -> `quality_blocked ['truncated_ending', 'missing_immediate_consequence']`
- reruns comparables budgets manifeste:
  - `ollama:qwen2.5:7b` -> `quality_blocked ['truncated_ending', 'missing_risky_decision', 'incomplete_scene']` dans `automation/reports/20260322_qwen2_5_7b_judge_budgeted`
  - `ollama:mistral-nemo:latest` -> `quality_blocked ['truncated_ending']` dans `automation/reports/20260322_mistral_nemo_judge_budgeted`
- retouche prompt + reruns:
  - `ollama:qwen2.5:7b` -> gain partiel: plus d'`incomplete_scene`, reste `quality_blocked ['truncated_ending', 'missing_risky_decision']` dans `automation/reports/20260322_qwen2_5_7b_judge_prompted`
  - `ollama:mistral-nemo:latest` -> regression: retour `outline_like` + `missing_immediate_consequence` dans `automation/reports/20260322_mistral_nemo_judge_prompted`
- correctif gate + retouche micro-decision :
  - `ollama:mistral-nemo:latest` -> faux `outline_like` supprime; reste `quality_blocked ['missing_immediate_consequence']` dans `automation/reports/20260322_mistral_nemo_judge_gatefix`
  - `ollama:qwen2.5:7b` -> `missing_risky_decision` supprime; reste `quality_blocked ['missing_immediate_consequence']` dans `automation/reports/20260322_qwen2_5_7b_judge_gatefix`
- retouche "consequence immediate observable" :
  - `ollama:qwen2.5:7b` -> `accepted` sans repair dans `automation/reports/20260322_qwen2_5_7b_judge_consequencefix`
  - `ollama:mistral-nemo:latest` -> regression vers `quality_blocked ['truncated_ending', 'missing_risky_decision', 'missing_immediate_consequence']` dans `automation/reports/20260322_mistral_nemo_judge_consequencefix`
- runtime utile du 22 mars:
  - `:8091` revalide localement via `llama-server` pour qwen et mistral
  - `:8110` repond a `/health` mais reste inutilisable pour `chat/completions`
  - `automation/next_lots.toml` repointe maintenant vers `/Users/electron/Documents/Projets/mascarade`
  - `scripts/smoke_local_generation.sh` aligne maintenant ses budgets non-Apple sur le manifeste (`rewrite=1024`, `repair=1536`)
- cote app (2026-03-25):
  - `app_AI-novel-engine` integre maintenant `Mascarade Core` et `Mascarade API` pour `agents`, `models` et `chat/completions`
  - le panneau `Generation` affiche `provider_status` (`actif`, `configure`, `unauthorized`, erreur runtime) et le preset recommande suit maintenant le premier modele reellement actif
  - un `Wizard Agents` dedie guide maintenant l'usage des agents Mascarade (`source -> catalogue -> brief -> routage -> run -> apply`) et persiste cet etat par projet
  - le `Wizard Agents` garde maintenant un historique recent des runs agent et affiche une comparaison `brouillon / sortie agent` avant application
  - le `Copilot / Writing Tools` sait lancer l'agent Mascarade selectionne, reinjecter sa reponse dans le fil Copilot, puis comparer inline `brouillon courant` / `derniere reponse Copilot` / `dernier manuscrit pipeline`
  - le lot `Copilot hybride` a demarre: les requetes Copilot passent maintenant par une couche `CopilotService` avec fallback automatique `Apple Intelligence -> backend`
  - le `Copilot` consomme maintenant un contexte ANE outille (`scene`, `brouillon`, `prompt`, `gate`, `manuscrit`, `agent`) prepare hors de l'UI pour les futures integrations `App Intents`
  - le `Copilot` ajoute maintenant un RAG local-first sur le graphe projet et les artefacts pipeline, avec visualisation des extraits recuperes dans l'app
  - les premieres actions outillees du `Copilot` sont maintenant reexecutables depuis le panneau de contexte (`scene`, `gate`, `manuscrit`, `agent`, `pipeline`)
  - les ecritures destructives du brouillon depuis le `Copilot` ou un agent Mascarade demandent maintenant confirmation
  - l'app expose maintenant un preset `MLX local` `:8092` avec `mlx-community/Ministral-3-3B-Instruct-2512-4bit` et un script `scripts/mlx_runtime.sh` pour diagnostiquer / demarrer le runtime
  - l'app expose maintenant une bibliotheque locale de modeles HF/MLX (cache HF dedie, conversion MLX, nettoyage source optionnel, activation) et un export dataset JSONL compatible `KIKI-models-tuning`
  - la refonte UI du 2 avril recentre maintenant l'app sur trois axes (`Ecrire`, `IA`, `Analyser & Ops`), avec un header a signaux et un inspecteur tabule `Contexte / Runtime / Pipeline`
  - un nouvel ecran `Runtime & modeles` centralise maintenant la configuration IA, les providers Mascarade, le runtime MLX, la bibliotheque locale HF/MLX et l'export dataset KIKI
  - les telechargements HF affichent maintenant une progression reelle, une annulation propre et un token HF optionnel cote app
  - l'app expose maintenant un preflight `compatibilite MLX`; `croissantllm/CroissantLLMChat-v0.1` est telecharge localement et classe `Convertible MLX`
  - `croissantllm/CroissantLLMChat-v0.1` a maintenant aussi un smoke reel MLX local valide (`~812M`, footprint stable `~3.7G`, pic `~6.7G`, `~1.0-1.8 s`), mais le replay ANE reel reste insuffisant (`repair_v1` corrompu, `gate/judge` fragiles), donc pas encore de promotion `Qualite FR`
  - le 2 avril, `mlx-community/Ministral-3-3B-Instruct-2512-4bit` a ete telecharge et valide en reel sur `:8092` (`health`, `v1/models`, `v1/chat/completions`)
  - le 2 avril, `mlx-community/Qwen2.5-7B-Instruct-4bit` a ete telecharge et rejoue en reel sur `:8092`; il tient le JSON parseable sur `gate/judge` sous `~4.9G` de footprint et `~5.7G` de pic memoire, mais pas encore le contrat ANE complet sans post-traitement schema/consistance
  - l'app expose maintenant un preset `Mistral local` pointant vers `http://127.0.0.1:8091` avec `ollama:mistral-nemo:latest` pour un chemin local type TurboQuant / llama.cpp
  - l'app expose aussi deux profils FR explicites: `croissantllm/CroissantLLMChat-v0.1` (`FR local experimental`) et `croissantllm/CroissantLLMBase` (`R&D ANE`)
  - reverification ANE du 2 avril: `mlx-community/Ministral-3-3B-Instruct-2512-4bit` sert bien un vrai `repair_v1` apres completion du cache, mais ni lui ni `CroissantLLMChat` ne respectent encore assez bien les contrats JSON `gate/judge` pour servir de moteur ANE strict local
  - le lot `App Intents` expose maintenant l'ouverture de l'app, le resume de scene, l'ouverture de scene ciblee, une aide de rewrite locale, et le lancement du pipeline ANE
  - la provenance exacte d'ecriture est maintenant persistee dans `DraftSnapshot.source` pour `Copilot`, agents, generation directe et pipeline
  - verification bundle app du 29 mars: `validate-app-intents` confirme que les symboles intents sont bien dans le binaire, mais que l'exposition systeme reste bloquee par l'absence de metadonnees `App Intents` et un Xcode local casse
- reverification runtime du 25 mars:
  - `Mascarade Core` `:8100` repond a `health` et `v1/models`
  - `Mascarade API` `:3100` repond a `health`, `v1/api/models` et `v1/api/agents/catalog`
  - `local_server` expose maintenant `provider_status` / `v1/providers/status` et ne publie plus les providers non autorises comme disponibles
  - `claude:claude-sonnet-4-6` passe maintenant en bout-en-bout sur `:8100/v1/chat/completions` et `:3100/api/v1/chat/completions`
  - `mistral` et `openai` restent configures localement, mais sont correctement marques `unauthorized`
- etat live reverifie (2026-03-16 session 3) :
  - `:8201` UP — `qwen3.5-4b-onnx-q4f16` actif
  - `:11434` UP
  - `:8100` UP (mascarade — `apple-coreml` + `ollama` providers)
  - `:8091` UP — `ollama:qwen2.5:7b` (dernier rerun gatefix)
  - lot `baselines` termine dans `automation/reports/20260316T195716Z/`
  - lot `priority_models` termine dans `automation/reports/20260316T211232Z/`
  - lot `french_models` termine dans `automation/reports/20260316T220423Z/`
- fix `outline_like` valide : `qwen2.5:1.5b` → `quality_blocked ['truncated_ending']` uniquement (plus d'`outline_like`)
- fix `dense_bullet_list` : 4+ bullet lines = `outline_like` sans 2e marqueur
- lot runtime extrait : `core/runtime/{config,models,client,health,policies}.py`
- suite unitaire : 156 tests verts
- le 2 avril, le pipeline ANE normalise maintenant les verdicts `gate/judge` avant persistence: aliases historiques (`incomplete`, `lacks_narrative_continuity`) unifies, labels inconnus filtres, doublons supprimes et `ready_for_manuscript` recalcule a partir des blockers effectifs

## Refonte runtime (P0)

- [x] P0 Extraire une couche runtime minimale (`RuntimeProfile`, client OpenAI-compatible, health probe)
- [x] P0 Formaliser les profils runtime nommes (`mascarade_local`, `mascarade_remote_*`, `llama_cpp_local`)
- [x] P0 Encoder la capacite `response_format` au lieu de la supposer pour tous les runtimes
- [x] P1 Sortir le preflight runtime et les checkpoints Apple / `llama.cpp` de `core/next_lots.py`
- [x] P1 Ajouter des tests dedies aux profils runtime et a la sante runtime

## Actif

### Qualite narrative (priorite P0 apres services)
- [x] P0 Revalider le fix `outline_like` sur `ollama:qwen2.5:1.5b` — confirme : `quality_blocked ['truncated_ending']` seulement
- [x] P0 Remonter `http://127.0.0.1:8100/health` — mascarade UP
- [x] P0 Requalifier `ollama:qwen2.5:7b` via `llama.cpp` / `llama-server` — `:8091` UP avec qwen2.5:7b
- [x] P0 Rejouer `priority_models` — en cours rapport `20260316T204232Z`
- [x] P1 Rejouer `french_models` (mistral-nemo) — `quality_blocked ['outline_like', 'incomplete', 'lacks_narrative_continuity']` (rapport `20260316T220423Z`)
- [x] P1 Analyser resultats `priority_models` et `french_models` — comparatif mis a jour (session 3)
- [x] P1 Garder `scripts/ops_tui.py` comme point d'entree exploitation court terme
- [x] P0 Ajouter un juge narratif secondaire optionnel (`core/evaluation/*`, `ANE_JUDGE_MODEL`) compatible avec une future grille type Prometheus
- [x] P0 Etendre `gate_v1.json`, `meta.json` et `_repair_focus()` avec le verdict du juge narratif
- [x] P1 Ajouter `prompts/judge_narrative_v1.txt` et resserrer `gate_v1` / `rewrite_v1` / `repair_v1` sur decision risquee + consequence immediate
- [x] P1 Rejouer `priority_models` avec `ANE_JUDGE_MODEL` pour requalifier `qwen2.5:7b` — verdict final `quality_blocked ['truncated_ending', 'missing_risky_decision']` (workspace `automation/reports/20260322_qwen2_5_7b_judge`)
- [x] P1 Rejouer `french_models` avec `ANE_JUDGE_MODEL` pour requalifier `mistral-nemo` — verdict final `quality_blocked ['truncated_ending', 'missing_immediate_consequence']` (workspace `automation/reports/20260322_mistral_nemo_judge`)
- [x] P1 Aligner `scripts/smoke_local_generation.sh` sur les budgets non-Apple du manifeste (`rewrite=1024`, `repair=1536`)
- [x] P1 Requalifier `qwen2.5:7b` et `mistral-nemo` avec les budgets du manifeste
- [x] P1 Tenter une retouche prompt courte sur fermeture de scene / non-repetition
- [x] P0 Retoucher `rewrite_v1` / `repair_v1` de maniere plus fine pour `qwen2.5:7b` sans degrader `mistral-nemo` — `missing_risky_decision` tombe sur `automation/reports/20260322_qwen2_5_7b_judge_gatefix`
- [x] P0 Renforcer `gate_v1` contre les faux `outline_like` LLM sur prose narrative francaise (`mistral-nemo` prompté) — valide sur `automation/reports/20260322_mistral_nemo_judge_gatefix`
- [x] P0 Retoucher `rewrite_v1` / `repair_v1` / `_repair_focus()` pour forcer une consequence immediate observable apres l'acte final, sans rouvrir la scene
- [x] P0 Rejouer `qwen2.5:7b` et `mistral-nemo` apres cette retouche ciblee "consequence immediate"
- [x] P0 Isoler une variante prompt/repair pour `mistral-nemo` — `rewrite_v2_nemo.txt` + `repair_v2_nemo.txt` + `prompt_profile` dans PromptStore
- [x] P0 Garder `qwen2.5:7b` comme baseline Ollama — passe dans priority_models via Mascarade P2P (2026-03-23)
- [x] P1 Durcir la normalisation schema/consistance des verdicts `gate/judge` pour les petits modeles locaux avant persistence ANE
- [ ] P1 Ajouter un post-traitement semantique optionnel pour les contradictions restantes (`summary` vs blockers) si on veut promouvoir `Qwen2.5-7B` comme evaluateur local ANE

### Qualite code (P1, lot refonte)
- [x] P0 Extraire une couche `core/runtime/*` claire (profil, contraintes, healthcheck) sans casser la facade `core/generation/provider.py`
- [x] P1 Faire converger `core/generation/provider.py` vers `core/runtime/config.py` pour eliminer la duplication de config runtime
- [x] P1 Faire consommer une partie de cette couche par `next_lots` et `ops_tui` (`runtime_probe_profile`, `runtime_model_ids`)
- [x] P1 Extraire hors de `next_lots` les checkpoints manuels Apple et le preflight Ollama natif vers `core/runtime/checkpoints.py` et `core/runtime/preflight.py`
- [x] P1 Ajouter des profils runtime explicites (`mascarade_local`, `mascarade_remote_*`, `apple_coreml_single_model`, `ollama_openai_compatible`, `llama_cpp_local`)
- [x] P1 Encoder `response_format` comme capacite runtime explicite plutot que supposition globale
- [x] P1 Faire converger `scripts/mascarade_remote_tui.py` et les preflights distants sur le registre de profils runtime
- [x] P1 Reduire encore `core/next_lots.py` au role orchestration + sync documentaire maintenant que `core/runtime/orchestration.py` existe
- [x] P1 Extraire la synchro documentaire residuelle dans `core/tracking_sync.py` pour garder `core/next_lots.py` sur l'orchestration, l'etat et l'execution de commandes
- [x] Fix 4 bare `except Exception` dans `core/next_lots.py` — restreints a `(OSError, json.JSONDecodeError, ValueError)`
- [x] Fix des `except Exception` restants sur chemins critiques (`core/next_lots.py` preflight + `scripts/ops_tui.py` probe URL)
- [x] Prompts `draft_v1`, `rewrite_v1`, `repair_v1` : output primer + few-shot BAD/GOOD
- [x] Tests `IntentionGate`, `PromptStore`, CLI intention — suite a 77 tests verts
- [x] `_finish_stage()` extrait dans `pipeline.py` — `generate_chapter()` -12 lignes
- [x] `_iter_chapters_with_status()` extrait dans `loader.py` — 3 fonctions factorisees
- [x] `Makefile` enrichi : `healthcheck`, `smoke-apple/ollama/mistral`, `lot-priority/baselines/french/full/sync`, `resume`, `test-v`
- [x] `README.md` nettoye : bloc CHANTIER:AUDIT stale supprime
- [ ] P2 Typer `metadata` avec `ChapterMetadata(TypedDict)` dans `pipeline.py` — reporte: 20+ signatures a changer, impact eleve pour gain faible avant reruns stables
- [x] P2 Robustifier `_close_json_delimiters()` dans `models.py` — closers mal assortis et stray closers geres, 3 nouveaux tests, 80 tests verts
- [x] Ecritures JSON atomiques (temp file + replace) sur `pipeline._write_json()` et `RunState.dump()`
- [x] Lectures metadata/index tolerantes aux JSON corrompus (`pipeline` + `loader`)

### Veille et docs (P2)

- [x] `docs/OSS_LANDSCAPE_2026-03-16.md` enrichi : GOAT, prometheus-eval, story-evaluation-llm, outlines, DeepEval, story-bench, lechmazur/writing, COLE FR benchmark
- [x] `docs/OSS_LANDSCAPE_2026-03-21.md` ajoute : veille sourcee runtime/eval pour guider la refonte ANE
- [x] `docs/OSS_RUNTIME_EVAL_2026-03-21.md` ajoute : synthese courte orientee runtime local, evals et generation structuree
- [x] `docs/AGENTS_2026-03-16.md` mis a jour avec Agent 6 Qualite code
- [x] `docs/FEATURE_MAP_2026-03-16.md` mis a jour avec Carte 7 Qualite code + french_models
- [x] README aligne manifeste (`principes`, `governance`) + runbook recovery
- [x] Nouveau runbook `docs/runbooks/RECOVERY_PROCEDURES.md` (resume lot, recovery metadata/state)
- [x] `docs/OSS_LANDSCAPE_2026-03-21.md` ajoute avec sources web et recommandations de refonte
- [x] P1 Realigner les plans/TODOs/docs de `app_AI-novel-engine` sur l'etat reel Mascarade + pipeline ANE
- [ ] P2 Evaluer `prometheus-eval` ou `story-evaluation-llm` comme remplacement gate heuristique — candidats confirmes (veille agent session 3)
- [ ] P2 Regarder `lm-format-enforcer` + `llama-cpp-python` comme premier fix logit anti-Markdown (plus facile qu'`outlines` selon veille)
- [ ] P2 Regarder `dottxt/outlines` pour contraintes logits si grammar sampling dispo dans llama-server
- [ ] P3 Tester CroissantLLM comme juge natif FR pour Prometheus sur sortie `mistral-nemo`


### Exploitation remote Mascarade (P0 nouveau)

- [x] P0 Ajouter un cockpit TUI remote `scripts/mascarade_remote_tui.py` pour `tower` et `kxkm`
- [x] P0 Ajouter la config centralisee `automation/mascarade_hosts.toml`
- [x] P0 Ajouter la persistance launchd (`scripts/setup_mascarade_launchd.py` + `automation/launchd/*.plist`)
- [x] P1 Ajouter les tests `tests/test_setup_mascarade_launchd.py`
- [ ] P0 Valider les tunnels SSH permanents (`8110` tower, `8111` kxkm) via session reelle
- [ ] P1 Activer launchd en reel (`install`) et verifier `status`
- [ ] P1 Optionnel: ajouter autossh si launchd seul ne suffit pas

## Bloque

- [ ] P0 `ollama` natif 0.17.7 sur macOS 26.3.1 / Apple M5 echoue encore en generation sur `qwen2.5:7b` et `qwen2.5:1.5b` avec une erreur Metal / `HTTP 500` — contourne via `llama-server` sur `:8091`
- [ ] P0 Les secrets locaux `Mistral` et `OpenAI` sont invalides/expirés sur cette machine; les corriger pour re-activer ces providers dans `Mascarade local_server`
- [ ] P1 Le runtime Apple local ne sert qu'un seul `model_id` a la fois; tout switch Apple reste semi-manuel (`prepare_runtime_step.sh`)
- [ ] P1 Le runtime remote `:8110` repond a `/health` mais reste inutilisable pour `POST /v1/chat/completions` (`Temporary failure in name resolution`)
- [x] P1 `:8100` ne repond pas — CORRIGE (mascarade relance, UP)
- [x] P1 `:8091` ne repond pas — CORRIGE (llama-server relance, UP avec qwen2.5:7b)

## Prochain ordre

- [x] P0 Remonter le core OpenAI-compatible `:8100` — mascarade UP
- [x] P0 Relancer `llama-server` sur `:8091` pour `qwen2.5:7b` — UP
- [ ] P0 Reprendre `priority_models`: checkpoint Apple en attente (`prepare_runtime_step.sh` puis `--resume`) si et seulement si un lot Apple est relance
- [x] P1 Lancer `python3 scripts/run_next_lots.py --lot french_models` — done, rapport `20260316T220423Z`
- [ ] P1 Garder `automation/reports/apple_rerun_preset_20260313T223555Z` comme rerun de reference pour les comparaisons Apple futures
- [x] P1 Verifier la purge reports en dry-run (`prune --days 14`) — 2 candidats, dont 1 reference a proteger
- [ ] P1 Garder `python3 scripts/reports_ops.py prune --days 14` en dry-run par defaut tant que les reports references ne sont pas marques
- [x] P1 Analyser logs et tenter purge chirurgicale (`analyze-logs --top 15`, `prune --days 14 --delete-workspaces`) — 0 suppression necessaire
- [x] P0 Brancher `priority_models` sur `ollama:qwen2.5:7b` — fait via Mascarade routing (2026-03-23)
- [ ] P0 Creer une retouche specifique `mistral-nemo` moins directive sur la structure de fin, puis rejouer `automation/reports/20260322_mistral_nemo_judge_consequencefix`

## Auto-sync
<!-- AUTO-SYNC:ANE-TODO-ACTIVE:START -->
- dernier cycle automatique: 2026-03-23T21:34:05+00:00
- modeles accepted: mistral:mistral-large-latest
- modeles ayant atteint gate: mistral:mistral-large-latest
- quality_blocked: aucun
- provider_failed: ollama:qwen2.5:7b, ollama:mistral-nemo:latest
- prochain lot recommande: Reference locale reconfirmee; retablir le runtime des modeles provider_failed avant de poursuivre.
- checkpoint manuel en attente: Le runtime Apple sert `aucun modèle` au lieu de `qwen3-4b-instruct-2507-q4f16`.
- commande preparee: `bash scripts/prepare_runtime_step.sh --apple-model qwen3-4b-instruct-2507-q4f16 --resume-state /Users/electron/Documents/Lelectron_rare/ai-novel-engine/automation/state/next_lots_state.json --ane-script /Users/electron/Documents/Lelectron_rare/ai-novel-engine/scripts/run_next_lots.py`
- reprise: `python3 scripts/run_next_lots.py --resume /Users/electron/Documents/Lelectron_rare/ai-novel-engine/automation/state/next_lots_state.json`
<!-- AUTO-SYNC:ANE-TODO-ACTIVE:END -->
