# TODO actif - AI Novel Engine

Source de verite des taches restantes pour `ai-novel-engine`.

Regle:
- cocher ici ce qui est fait puis deplacer le lot livre vers `TODO_IMPLEMENTE.md`
- ne suivre ici que le travail restant ou les blocages encore ouverts
- garder les dependances `mascarade` explicites

## Deja implemente
- [x] P0 Pipeline chapitre `intention -> structure -> draft -> critique -> rewrite -> validation -> memoire`
- [x] P0 Normalisation de chapitre avec identifiant canonique `chapitre_XX` et detection des collisions legacy
- [x] P0 Provider OpenAI-compatible et branchement local via `mascarade`
- [x] P0 Budgets par etape (`ANE_MAX_TOKENS_*`)
- [x] P0 Parsing JSON tolerant pour les sorties locales imparfaites
- [x] P0 Second passage de reessai pour `critique` et `memory` si le JSON reste invalide apres parsing tolerant
- [x] P0 Garde-fou manuscrit dur avant promotion (`gate_v1.json`, heuristiques locales, verdict `quality_blocked`)
- [x] P0 Boucle `repair` automatique entre `gate` et `quality_blocked`, avec artefacts `repair_vN.md`, fallback modele et preservation de `draft_v2.md`
- [x] P0 Smoke script local `scripts/smoke_local_generation.sh`
- [x] P0 Timeout provider remonte maintenant en `ProviderError` et marque correctement `failed_stage` dans `meta.json`
- [x] P0 Warm-up Apple du smoke remonte maintenant une erreur lisible au lieu d'une stacktrace brute
- [x] P0 Prompts `draft_v1` et `rewrite_v1` durcis pour imposer une prose continue sans titres ni puces
- [x] P1 Flags CLI non interactifs `--approve` et `--reject`
- [x] P1 `status` enrichi avec les chapitres en echec, en attente et bloques par garde-fou
- [x] P1 Resume de smoke humain a partir du `meta.json`
- [x] P1 Contrat cross-repo et recovery documentes via les runbooks
- [x] P2 `docs/vision.md`, `docs/roadmap.md` et le runbook local ne sont plus des placeholders
- [x] P0 Revalidation sous garde-fou de `ollama:qwen2.5:1.5b` -> `quality_blocked`
- [x] P0 Revalidation sous garde-fou de `apple-coreml:qwen2.5-0.5b-instruct-onnx` -> `quality_blocked`
- [x] P0 Revalidation sous garde-fou de `apple-coreml:qwen3.5-4b-onnx-q4f16` -> `provider_failed` en `rewrite`
- [x] P0 Revalidation sous garde-fou de `ollama:qwen2.5:7b` -> `provider_failed` par timeout en `draft`
- [x] P0 Comparatif local re-ecrit pour le protocole avec garde-fou dans `docs/MODEL_COMPARISON_2026-03-08.md`
- [x] P0 Revalidation reelle sous protocole `gate + repair` borne a `300s` par requete:
  - `ollama:qwen2.5:1.5b` -> `failed` en `structure`
  - `apple-coreml:qwen2.5-0.5b-instruct-onnx` -> `failed` en `rewrite`
  - `apple-coreml:qwen3.5-4b-onnx-q4f16` -> `failed` en `rewrite`
  - `ollama:qwen2.5:7b` -> `failed` en `rewrite`

## Actif
- [ ] P0 Terminer le lot `baselines`, puis relancer `tracking_sync` sur un etat complet incluant `apple-coreml:qwen2.5-0.5b-instruct-onnx` et `ollama:qwen2.5:1.5b`
- [ ] P0 Faire passer `ollama:qwen2.5:7b` de `quality_blocked` a `accepted` en supprimant le residu `outline_like` apres `repair`
- [ ] P0 Faire terminer au moins un cycle `python3 scripts/run_next_lots.py --lot full` jusqu'a `tracking_sync` sans checkpoint manuel autre qu'un switch Apple explicite
- [ ] P1 Requalifier `apple-coreml:qwen3.5-4b-onnx-q4f16` comme reference Apple stable sur plusieurs cycles, pas sur un seul run accepte
- [ ] P1 Rendre la strategie de fallback `repair` consciente des modeles reellement servis: le runtime Apple n'expose qu'un `model_id` a la fois
- [ ] P1 Garder l'installation/staging Apple de `qwen2.5-0.5b-instruct-onnx`, `qwen3.5-4b-onnx-q4f16` et `stateful-mistral7b-instruct-int4-coreml` comme prerequis explicite

## Bloque
- [ ] P1 `ollama:qwen2.5:7b` atteint maintenant `gate` et exerce `repair`, mais reste bloque sur `outline_like` apres deux passes
- [ ] P1 Le lot `baselines` exige encore un switch Apple explicite avant de pouvoir finir `apple-coreml:qwen2.5-0.5b-instruct-onnx`
- [ ] P1 `ollama:qwen2.5:1.5b` reste lent et reste a requalifier une fois `baselines` repris jusqu'au bout
- [ ] P1 `apple-coreml:stateful-mistral7b-instruct-int4-coreml` reste preflight-only sur cette machine: preflight froid `:8100` OK en 128 s, preflight chaud OK en 63 s, mais le smoke ANE est reste bloque a `structure` pendant plus de 8 minutes avec les budgets de smoke
- [ ] P1 Le host `ollama` natif 0.17.7 sur cette machine echoue sur `qwen2.5:1.5b` avec un crash Metal; la validation ANE reelle passe par un service Docker CPU expose sur `127.0.0.1:11435` et route via `mascarade`
- [ ] P1 Le runtime Apple local n'expose qu'un seul `model_id` a la fois; un fallback `repair` vers un autre modele Apple exige donc un switch de service entre deux runs, pas au milieu d'un smoke

## Prochain ordre
- [ ] P0 Finir `python3 scripts/run_next_lots.py --lot baselines`, puis laisser `tracking_sync` recalculer les verdicts complets
- [ ] P0 Tuner `rewrite_v1` et la passe `repair` pour eliminer `outline_like` sur `ollama:qwen2.5:7b`
- [ ] P1 Rejouer ensuite `python3 scripts/run_next_lots.py --lot priority_models` pour verifier la stabilite de `apple-coreml:qwen3.5-4b-onnx-q4f16` et le sort de `ollama:qwen2.5:7b`
- [ ] P1 Garder `apple-coreml:qwen2.5-0.5b-instruct-onnx` et `ollama:qwen2.5:1.5b` comme baselines vitesse ou regressions tant qu'ils n'ont pas de verdict comparable au protocole courant
- [ ] P1 Verifier avant tout rerun Apple que `qwen2.5-0.5b-instruct-onnx`, `qwen3.5-4b-onnx-q4f16` et `stateful-mistral7b-instruct-int4-coreml` sont bien installes/stages et que le bon `model_id` est charge sur `:8201`

## Auto-sync
## Auto-sync
<!-- AUTO-SYNC:ANE-TODO-ACTIVE:START -->
- dernier cycle automatique: 2026-03-09T06:53:02+00:00
- modeles accepted: aucun
- modeles ayant atteint gate: apple-coreml:qwen2.5-0.5b-instruct-onnx, ollama:qwen2.5:1.5b
- quality_blocked: apple-coreml:qwen2.5-0.5b-instruct-onnx, ollama:qwen2.5:1.5b
- provider_failed: aucun
- prochain lot recommande: Analyser les runs ayant atteint gate/repair puis resserrer la reference locale autour des meilleurs candidats.
- checkpoint manuel en attente: Le runtime Apple sert `qwen2.5-0.5b-instruct-onnx` au lieu de `stateful-mistral7b-instruct-int4-coreml`.
- commande preparee: `bash scripts/prepare_runtime_step.sh --apple-model stateful-mistral7b-instruct-int4-coreml --resume-state /Users/electron/Documents/Projets_Creatifs/ai-novel-engine/automation/state/next_lots_state.json --ane-script /Users/electron/Documents/Projets_Creatifs/ai-novel-engine/scripts/run_next_lots.py`
- reprise: `python3 scripts/run_next_lots.py --resume /Users/electron/Documents/Projets_Creatifs/ai-novel-engine/automation/state/next_lots_state.json`
<!-- AUTO-SYNC:ANE-TODO-ACTIVE:END -->
