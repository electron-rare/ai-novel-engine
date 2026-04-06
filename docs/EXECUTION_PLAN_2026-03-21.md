# Plan d'execution - 21 mars 2026

Plan de reprise reel base sur l'etat code, docs et reports constate le 21 mars 2026.

References:

- contexte: [`CONTEXTE_PROJET_2026-03-21.md`](./CONTEXTE_PROJET_2026-03-21.md)
- memoire: [`MEMOIRE_REPRISE_2026-03-21.md`](./MEMOIRE_REPRISE_2026-03-21.md)
- spec systeme: [`SYSTEM_SPEC_2026-03-21.md`](./SYSTEM_SPEC_2026-03-21.md)
- carte agents: [`AGENTS_2026-03-21.md`](./AGENTS_2026-03-21.md)
- backlog actif: [`../TODO_ACTIVE.md`](../TODO_ACTIVE.md)

## Lot 1 - Extraire la couche runtime minimale [LIVRE]

- `core/runtime/config.py` : configuration runtime partagee et budgets par etape
- `core/runtime/models.py` : `RuntimeProfile`, `RuntimeCapabilities`, `RuntimeHealth`
- `core/runtime/policies.py` : fallback `repair`, detection provider, contrainte Apple
- `core/runtime/client.py` : client OpenAI-compatible avec retries et normalisation du texte
- `core/runtime/health.py` : health probe simple
- `core/generation/provider.py` garde l'API publique mais s'appuie sur `OpenAICompatibleRuntimeConfig` + le client runtime
- `core/generation/pipeline.py` delegue maintenant la politique de fallback runtime a `core/runtime/policies.py`
- `core/next_lots.py` reutilise deja `runtime_probe_profile` et `runtime_model_ids`
- `core/next_lots.py` recompilable a nouveau
- suite Python a `128` tests verts

## Lot 2 - Formaliser profils et capacites runtime [LIVRE]

### Objectif

- sortir les decisions runtime des details implicites disperses dans le pipeline, puis finir de les sortir de `next_lots`

### Done quand

- `provider.py` lit la config runtime partagee
- `next_lots.py` et `ops_tui.py` consomment `runtime_probe_profile()` / `runtime_model_ids()`
- profils explicites `mascarade_local`, `mascarade_remote_*`, `llama_cpp_local`
- metadata et preflight lisent ces capacites au lieu de les redeviner

Etat:

- `provider.py` lit la config runtime partagee
- `next_lots.py` et `ops_tui.py` consomment les probes runtime partagees
- `core/runtime/profiles.py` formalise les noms de profils/probes
- `response_format` est encode comme capacite runtime explicite
- suite Python a `152` tests verts

## Lot 3 - Refaire `next_lots`, `ops_tui` et les preflights autour de la couche runtime [LIVRE]

### Objectif

- reduire le couplage entre orchestration, checkpoints manuels et synchronisation documentaire

### Done quand

- preflight runtime isole
- checkpoint Apple / `llama.cpp` isole
- auto-sync docs garde, mais hors logique de sante runtime

Etat:

- checkpoint Apple et preflight Ollama natif deja extraits vers `core/runtime/*`
- `scripts/mascarade_remote_tui.py` et `scripts/setup_mascarade_launchd.py` consomment maintenant `core/runtime/remote_hosts.py`
- `core/runtime/orchestration.py` extrait le plan runtime, les signaux checkpoint et le catalogue Ollama hors de `next_lots`
- `core/tracking_sync.py` extrait la synchronisation documentaire et les rendus auto-sync hors de `next_lots`
- `core/next_lots.py` est recentre sur orchestration, etat et commandes
- prochaine extraction utile: consolider les tests orchestration vs sync et garder le reste du control plane mince

## Lot 4 - Ajouter un juge narratif secondaire [LIVRE]

### Objectif

- ajouter une seconde lecture narrative compatible avec une future integration Prometheus, sans dependance externe

### Etat

- `core/evaluation/` ajoute `NarrativeJudge` et `ProviderNarrativeJudge`
- le juge est optionnel et active via `ANE_JUDGE_MODEL`
- `gate_v1.json` / `meta.json` exposent `judge_report` et `judge_blockers`
- `_repair_focus()` et les prompts `gate`, `rewrite`, `repair` sont resserres sur decision risquee et consequence immediate
- suite Python a `155` tests verts

## Lot 5 - Revenir aux blockers narratifs utiles [EN COURS]

### Objectif

- retoucher prompts et gate seulement apres stabilisation de la lecture runtime

### Cibles

- `qwen2.5:7b` : fermer la scene sur la decision risquee attendue
- `mistral-nemo` : comprendre la condensation a 316 mots
- ne pas surcorriger les petits modeles 0.5b / 1.5b au-dela de leur envelope reelle

## Lot 6 - Realigner l'app SwiftUI [LIVRE]

### Objectif

- faire raconter a l'app la meme architecture que le moteur Python

### Done quand

- docs app mises a jour sur Mascarade + pipeline ANE
- backlog app aligne sur l'etat reel
- strategie de tests Swift clarifiee

Etat:

- l'app sait deja parler a `OpenAI` direct ou `Mascarade`
- le pipeline ANE complet est deja lancable depuis l'app
- le panneau workspace ANE expose maintenant les artefacts utiles et les erreurs pipeline/runtime
- `Package.swift` expose un `testTarget`
- `DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swift test` passe
- README, TODOs et docs app ont ete resynchronises
## Lot 7 - Hygiene reports / logs

### Objectif

- garder une retention utile sans perdre les evidence packs cites comme references

### Done quand

- les reports historiques a conserver sont marques comme tels
- les purges automatiques ne proposent plus de supprimer une reference documentaire

## Risque a eviter

Ne pas rebasculer vers du tuning prompt tant que les capacites runtime ne sont pas encodees explicitement dans ANE.
