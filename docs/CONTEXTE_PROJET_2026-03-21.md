# Contexte projet - 21 mars 2026

Photographie courte du repo `ai-novel-engine` apres integration Mascarade dans l'app, extraction runtime cote Python et ajout d'un juge narratif secondaire.

## Intention

Conserver ANE comme moteur narratif strict, relancable et inspectable, tout en traitant enfin le runtime comme une couche dediee et non comme un detail enfoui dans le provider.

## Etat reel

- le moteur Python reste la source de verite pour le pipeline `intention -> structure -> draft -> critique -> rewrite -> gate -> repair -> memory`
- une premiere couche runtime existe desormais sous `core/runtime/` :
  - `models.py`
  - `client.py`
  - `health.py`
  - `config.py`
  - `policies.py`
- `core/generation/provider.py` delegue maintenant le transport OpenAI-compatible a `OpenAIChatRuntimeClient`
- `core/generation/pipeline.py` delegue maintenant le fallback `repair` a `core/runtime/policies.py`
- `core/evaluation/` ajoute un juge narratif secondaire optionnel, branche dans le gate via `ANE_JUDGE_MODEL`
- `core/next_lots.py` et `scripts/ops_tui.py` utilisent maintenant des helpers runtime partages pour les probes OpenAI-compatibles
- `core/runtime/profiles.py` formalise maintenant les noms de profils et de probes runtime utilises par l'orchestration
- `core/runtime/remote_hosts.py` factorise maintenant les hosts remote Mascarade pour le TUI remote et `launchd`
- `core/runtime/orchestration.py` porte maintenant le plan d'execution runtime et les signaux de checkpoint utilises par `next_lots`
- `core/next_lots.py` ne porte plus directement la logique de checkpoint Apple ni le preflight Ollama natif
- la suite Python passe a `155` tests verts
- les reports confirment toujours `apple-coreml:qwen3.5-4b-onnx-q4f16` comme seule reference `accepted`
- `ollama:qwen2.5:7b`, `ollama:qwen2.5:1.5b`, `ollama:mistral-nemo:latest` et `apple-coreml:qwen2.5-0.5b-instruct-onnx` atteignent bien `gate`, mais restent `quality_blocked`

## Etat ops utile

- `scripts/reports_ops.py summary` :
  - `reports=27`
  - `accepted=4`
  - `quality_blocked=15`
  - `provider_failed=7`
- `scripts/reports_ops.py analyze-logs --top 10` :
  - bruit dominant `HTTP 500`
  - un timeout client
- `scripts/reports_ops.py prune --days 14` propose 2 suppressions en dry-run, mais l'une est une reference explicitement conservee

## Etat app utile

- l'app SwiftUI sait maintenant choisir `OpenAI direct` ou `Mascarade`
- elle sait tester la connexion, appliquer un preset recommande, et lancer le pipeline ANE via `ANEPipelineService`
- elle expose maintenant un panneau workspace ANE et ses docs de pilotage ont ete resynchronisees

## Ce qui n'est toujours pas resolu

- les reruns `qwen2.5:7b` et `mistral-nemo` doivent etre rejoues avec le juge narratif secondaire pour confirmer le gain reel
- le contrat `response_format` n'est pas fiable de bout en bout si le shim Mascarade ne le propage pas
- les contraintes runtime Apple restent semi-manuelles et doivent devenir des capacites explicites dans ANE
