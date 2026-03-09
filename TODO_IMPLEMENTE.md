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

## Actif
- [x] Aucun suivi actif ici. Voir `TODO_ACTIVE.md`.

## Bloque
- [x] Aucun blocage suivi ici. Voir `TODO_ACTIVE.md`.

## Prochain ordre
- [x] Mettre a jour ce fichier uniquement quand un nouveau lot est reellement termine.

## Auto-sync
## Auto-sync
<!-- AUTO-SYNC:ANE-TODO-DONE:START -->
- orchestrateur `scripts/run_next_lots.py` disponible
- manifeste `automation/next_lots.toml` charge
- derniers fichiers de suivi synchronisables via marqueurs `AUTO-SYNC`
- dernier cycle automatise observe: 2026-03-09T06:53:02+00:00
<!-- AUTO-SYNC:ANE-TODO-DONE:END -->
