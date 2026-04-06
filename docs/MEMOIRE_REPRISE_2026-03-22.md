# Memoire de reprise - 22 mars 2026

Memoire operationnelle pour reprendre `ai-novel-engine` apres la vague de reruns cibles avec juge narratif.

## Etat code

- `core/runtime/` reste la couche runtime partagee unique pour config, profils, probes, checkpoints et orchestration
- `core/evaluation/` porte le juge narratif secondaire active par `ANE_JUDGE_MODEL`
- la refonte code reste stable; la session a ajoute une sanitization `outline_like` cote gate, une retouche micro-decision dans les prompts et une requalification narrative complete
- suite Python revalidee a `156` tests verts

## Etat runtime utile

- `llama-server` local sur `:8091` a ete prouve en chargeant puis servant effectivement :
  - `ollama:qwen2.5:7b`
  - `ollama:mistral-nemo:latest`
- `:8110` repond a `/health` mais reste inutilisable pour ANE tant que `POST /v1/chat/completions` echoue avec `Temporary failure in name resolution`
- le repo Mascarade local reel est `/Users/electron/Documents/Projets/mascarade`
- le chemin de demarrage Apple confirme cote Mascarade est :
  1. stage/export du modele
  2. exports `APPLE_LLM_*`
  3. `bash scripts/run_apple_llm_service.sh`

## Etat narratif utile

- qwen rerun juge :
  - workspace : `automation/reports/20260322_qwen2_5_7b_judge`
  - verdict : `quality_blocked`
  - blockers finaux : `truncated_ending`, `missing_risky_decision`
- mistral rerun juge :
  - workspace : `automation/reports/20260322_mistral_nemo_judge`
  - verdict : `quality_blocked`
  - blockers finaux : `truncated_ending`, `missing_immediate_consequence`
- qwen rerun budgete :
  - workspace : `automation/reports/20260322_qwen2_5_7b_judge_budgeted`
  - verdict : `quality_blocked`
  - blockers finaux : `truncated_ending`, `missing_risky_decision`, `incomplete_scene`
- mistral rerun budgete :
  - workspace : `automation/reports/20260322_mistral_nemo_judge_budgeted`
  - verdict : `quality_blocked`
  - blockers finaux : `truncated_ending`
- qwen rerun apres retouche prompt :
  - workspace : `automation/reports/20260322_qwen2_5_7b_judge_prompted`
  - gain partiel : `incomplete_scene` disparait
  - blockers finaux : `truncated_ending`, `missing_risky_decision`
- mistral rerun apres retouche prompt :
  - workspace : `automation/reports/20260322_mistral_nemo_judge_prompted`
  - regression : `outline_like`, `missing_immediate_consequence`
- mistral rerun apres correctif gate :
  - workspace : `automation/reports/20260322_mistral_nemo_judge_gatefix`
  - verdict : `quality_blocked`
  - blockers finaux : `missing_immediate_consequence`
- qwen rerun apres retouche micro-decision + gate stable :
  - workspace : `automation/reports/20260322_qwen2_5_7b_judge_gatefix`
  - verdict : `quality_blocked`
  - blockers finaux : `missing_immediate_consequence`
- qwen rerun apres retouche consequence immediate :
  - workspace : `automation/reports/20260322_qwen2_5_7b_judge_consequencefix`
  - verdict : `accepted`
  - aucun repair necessaire
- mistral rerun apres retouche consequence immediate :
  - workspace : `automation/reports/20260322_mistral_nemo_judge_consequencefix`
  - verdict : `quality_blocked`
  - blockers finaux : `truncated_ending`, `missing_risky_decision`, `missing_immediate_consequence`
- implication :
  - le juge secondaire est utile; il remplace un diagnostic narratif flou par des manques localises et exploitables
  - `qwen2.5:7b` a maintenant un chemin local stable jusqu'a `accepted`
  - la meme retouche ne generalise pas a `mistral-nemo`; il faut vraisemblablement separer le guidage de fin de scene par famille de modele

## Priorite immediate

1. Garder `automation/reports/20260322_qwen2_5_7b_judge_consequencefix` comme premiere reference Ollama `accepted`.
2. Isoler une variante prompt/repair moins directive pour `mistral-nemo`, puis rejouer `automation/reports/20260322_mistral_nemo_judge_consequencefix`.
3. Corriger ou contourner le faux positif ops du runtime remote `:8110`.
4. Ne reouvrir Apple `:8201` que pour un lot dedie, pas pour les reruns Ollama courants.
