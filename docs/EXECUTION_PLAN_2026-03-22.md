# Plan d'execution - 22 mars 2026

Plan de reprise reel base sur les reruns narratifs du 22 mars 2026 et sur l'etat runtime constate localement.

References:

- contexte: [`CONTEXTE_PROJET_2026-03-22.md`](./CONTEXTE_PROJET_2026-03-22.md)
- memoire: [`MEMOIRE_REPRISE_2026-03-22.md`](./MEMOIRE_REPRISE_2026-03-22.md)
- spec systeme: [`SYSTEM_SPEC_2026-03-21.md`](./SYSTEM_SPEC_2026-03-21.md)
- carte agents: [`AGENTS_2026-03-21.md`](./AGENTS_2026-03-21.md)
- backlog actif: [`../TODO_ACTIVE.md`](../TODO_ACTIVE.md)

## Lot 1 - Couche runtime minimale [LIVRE]

- `core/runtime/config.py` : configuration runtime partagee et budgets par etape
- `core/runtime/models.py` : `RuntimeProfile`, `RuntimeCapabilities`, `RuntimeHealth`
- `core/runtime/policies.py` : fallback `repair`, detection provider, contrainte Apple
- `core/runtime/client.py` : client OpenAI-compatible avec retries et normalisation du texte
- `core/runtime/health.py` : probes runtime
- `core/generation/provider.py` garde l'API publique mais s'appuie sur la config runtime partagee

## Lot 2 - Recentrage orchestration / sync [LIVRE]

- `core/runtime/orchestration.py` porte le plan runtime et les signaux de checkpoint
- `core/tracking_sync.py` porte la synchronisation documentaire
- `core/next_lots.py` est recentre sur orchestration, etat et commandes

## Lot 3 - Juge narratif secondaire [LIVRE]

- `core/evaluation/` ajoute `NarrativeJudge` et `ProviderNarrativeJudge`
- le juge est optionnel via `ANE_JUDGE_MODEL`
- `gate_v1.json` et `meta.json` exposent `judge_report` et `judge_blockers`
- `_repair_focus()` sait maintenant pousser `missing_risky_decision` et `missing_immediate_consequence`

## Lot 4 - Requalification narrative ciblee [LIVRE]

### Rerun `qwen2.5:7b`

- runtime : `llama.cpp` local sur `:8091`
- juge : `ANE_JUDGE_MODEL=ollama:qwen2.5:7b`
- workspace : `automation/reports/20260322_qwen2_5_7b_judge`
- verdict : `quality_blocked`
- blockers finaux : `truncated_ending`, `missing_risky_decision`

### Rerun `mistral-nemo`

- runtime : `llama.cpp` local sur `:8091`
- juge : `ANE_JUDGE_MODEL=ollama:mistral-nemo:latest`
- workspace : `automation/reports/20260322_mistral_nemo_judge`
- verdict : `quality_blocked`
- blockers finaux : `truncated_ending`, `missing_immediate_consequence`

### Lecture

- le juge secondaire produit bien un diagnostic plus fin que le gate heuristique seul
- `qwen2.5:7b` reste faible sur la cout/irreversibilite de la decision finale
- `mistral-nemo` garde la decision, mais echoue encore a montrer une consequence immediate

## Lot 5 - Gate sanitize + micro-decision [LIVRE]

### Objectif

- transformer les nouveaux diagnostics du juge en corrections de prompts et de repairs, pas en nouvelle complexite runtime

### Priorites

1. faire une retouche de prompt plus fine, ciblee sur `qwen2.5:7b`, pour fermer la scene sans boucle ni repetition
2. renforcer `gate_v1` contre les faux `outline_like` LLM sur prose narrative correcte
3. revalider ensuite `mistral-nemo` seulement apres cette correction gate/prompt plus fine
4. corriger le faux positif ops du runtime remote `:8110`

### Etat courant des reruns

- `qwen2.5:7b` :
  - rerun juge simple : `truncated_ending`, `missing_risky_decision`
  - rerun budgets manifeste : `truncated_ending`, `missing_risky_decision`, `incomplete_scene`
  - rerun prompté : `truncated_ending`, `missing_risky_decision` avec meilleur signal de structure
  - rerun gatefix : `missing_immediate_consequence` uniquement
- `mistral-nemo` :
  - rerun juge simple : `truncated_ending`, `missing_immediate_consequence`
  - rerun budgets manifeste : `truncated_ending`
  - rerun prompté : regression `outline_like`, `missing_immediate_consequence`
  - rerun gatefix : `missing_immediate_consequence` uniquement

### Lecture mise a jour

- le correctif `outline_like` est valide : `mistral-nemo` n'est plus bloque sur un faux positif de forme
- la retouche micro-decision est valide : `qwen2.5:7b` n'est plus bloque sur `missing_risky_decision`
- le prochain chantier utile est maintenant unique et partage : forcer une consequence immediate observable apres l'acte final, sans rouvrir une nouvelle scene

## Lot 6 - Consequence immediate observable [LIVRE]

### Objectif

- faire converger `qwen2.5:7b` et `mistral-nemo` vers un premier verdict `accepted` en fermant la consequence de l'acte final au lieu de simplement l'annoncer

### Priorites

1. retoucher `rewrite_v1` et `repair_v1` pour exiger une consequence immediate visible dans les 1-3 phrases suivant l'acte final
2. durcir `_repair_focus()` sur `missing_immediate_consequence` avec exemples de consequence observable et interdiction de reouvrir une nouvelle piste
3. rejouer `qwen2.5:7b` sur `:8091`
4. rejouer `mistral-nemo` sur `:8091`

### Resultat

- `qwen2.5:7b` : `accepted` dans `automation/reports/20260322_qwen2_5_7b_judge_consequencefix`
- `mistral-nemo` : regression dans `automation/reports/20260322_mistral_nemo_judge_consequencefix` vers `truncated_ending`, `missing_risky_decision`, `missing_immediate_consequence`

## Lot 7 - Divergence par famille de modele [A LANCER]

### Objectif

- conserver le gain `qwen2.5:7b` sans imposer a `mistral-nemo` une rigidite de fin de scene qu'il degrade

### Priorites

1. garder `qwen2.5:7b` comme baseline Ollama locale `accepted`
2. isoler une variante prompt/repair plus legere pour `mistral-nemo`
3. rejouer `mistral-nemo` apres cette separation
4. seulement ensuite, relancer `priority_models` complet avec `qwen2.5:7b` comme reference Ollama

## Risque a eviter

Ne pas confondre "runtime joignable" et "runtime exploitable" : `:8110` repond a `/health`, mais pas aux runs utiles ANE.

## Auto-sync
<!-- AUTO-SYNC:ANE-PLAN:START -->
- dernier verdict automatise: 2026-03-23T21:34:05+00:00
- accepted: mistral:mistral-large-latest
- gate atteint: mistral:mistral-large-latest
- prochain lot calcule: Reference locale reconfirmee; retablir le runtime des modeles provider_failed avant de poursuivre.
- checkpoint manuel requis: Le runtime Apple sert `aucun modèle` au lieu de `qwen3-4b-instruct-2507-q4f16`.
<!-- AUTO-SYNC:ANE-PLAN:END -->
