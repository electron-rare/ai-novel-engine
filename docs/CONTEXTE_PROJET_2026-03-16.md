# Contexte projet - 16 mars 2026

Document court pour reprendre `ai-novel-engine` sans relire tout l'historique.

## Ce que fait le projet

`ai-novel-engine` est un moteur de redaction longue local-first, structure autour d'un pipeline strict:

`intention -> structure -> draft -> critique -> rewrite -> gate -> validation -> memoire`

Ce n'est ni un chat libre ni un studio collaboratif. Le produit utile est:

- une chaine de production narrative lisible
- des artefacts markdown/json inspectables
- un garde-fou dur avant promotion manuscrit
- une memoire externe rejouable
- un runtime local interchangeable derriere un contrat OpenAI-compatible

## Etat confirme

- la reference locale reste `apple-coreml:qwen3.5-4b-onnx-q4f16`
- `apple-coreml:qwen2.5-0.5b-instruct-onnx` reste une baseline `quality_blocked`
- le chemin alternatif `llama.cpp` / `llama-server` pour `ollama:*` est maintenant branche cote orchestration ANE
- un smoke reel via ce chemin a deja fait passer `ollama:qwen2.5:1.5b` jusqu'au garde-fou, avec verdict `quality_blocked` sur `truncated_ending` et `outline_like`
- le blocage principal n'est donc plus "est-ce que le modele repond", mais "comment rendre ce chemin runtime stable et rejouable pour les lots automatisés"

## Etat live reverifie le 16 mars 2026

- `http://127.0.0.1:8100/health`: indisponible au moment du controle
- `http://127.0.0.1:8201/models`: OK, sert `qwen3.5-4b-onnx-q4f16`
- `http://127.0.0.1:8091/health`: indisponible au moment du controle
- `http://127.0.0.1:11434/api/tags`: OK, expose bien `qwen2.5:7b` et `qwen2.5:1.5b`

Lecture utile:

- le runtime Apple est en ligne
- le host Ollama expose toujours les tags et les blobs
- le core OpenAI-compatible `:8100` et le runtime alternatif `:8091` sont actuellement a remonter avant de relancer les lots utiles

## Ou on en est cote produit

- le pipeline narratif est stable et teste
- la boucle `repair` et le `gate` sont en production
- l'orchestrateur `next_lots` sait maintenant checkpoint-er proprement un runtime `llama-server`
- un cockpit TUI d'exploitation existe maintenant pour suivre projet, automation, reports et erreurs stderr

## Ce qui est vraiment bloque

- remettre `:8100` en service pour le flux nominal
- remettre `:8091` en service quand on veut valider `ollama:*` via `llama.cpp`
- rejouer `priority_models` puis `baselines` sur le nouveau chemin runtime
- reprendre `rewrite` / `repair` uniquement apres ces reruns

## Fichiers a ouvrir en premier

- [`docs/MEMOIRE_REPRISE_2026-03-16.md`](./MEMOIRE_REPRISE_2026-03-16.md)
- [`docs/EXECUTION_PLAN_2026-03-16.md`](./EXECUTION_PLAN_2026-03-16.md)
- [`docs/SYSTEM_SPEC_2026-03-16.md`](./SYSTEM_SPEC_2026-03-16.md)
- [`docs/FEATURE_MAP_2026-03-16.md`](./FEATURE_MAP_2026-03-16.md)
- [`docs/AGENTS_2026-03-16.md`](./AGENTS_2026-03-16.md)
- [`docs/OSS_LANDSCAPE_2026-03-16.md`](./OSS_LANDSCAPE_2026-03-16.md)
