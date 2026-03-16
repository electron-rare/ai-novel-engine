# Contexte projet - 14 mars 2026

Document court pour comprendre rapidement ou en est `ai-novel-engine` aujourd'hui.

## Ce que fait le projet

`ai-novel-engine` est un moteur de redaction longue qui garde l'auteur dans la boucle.

Le pipeline reste stable:

`intention -> structure -> draft -> critique -> rewrite -> gate -> validation -> memoire`

Le coeur produit n'est pas un "chat", mais une chaine de production narrative avec:

- intention obligatoire avant toute generation
- garde-fou dur avant promotion manuscrit
- boucle `repair`
- memoire externe par chapitre

## Architecture locale

Sur cette machine:

- `ai-novel-engine` parle un provider OpenAI-compatible
- `mascarade-core` expose `http://127.0.0.1:8100`
- le runtime Apple local expose `http://127.0.0.1:8201`
- Ollama natif expose `http://127.0.0.1:11434`

Le routage actuel repose surtout sur le prefixe de modele:

- `apple-coreml:*`
- `ollama:*`

## Etat produit confirme

- la reference locale reste `apple-coreml:qwen3.5-4b-onnx-q4f16`
- le comparatif versionne montre aujourd'hui:
  - `apple-coreml:qwen3.5-4b-onnx-q4f16` -> `accepted`
  - `apple-coreml:qwen2.5-0.5b-instruct-onnx` -> `quality_blocked`
  - `ollama:qwen2.5:7b` -> `provider_failed`
  - `ollama:qwen2.5:1.5b` -> `provider_failed`
- `python3 -m unittest discover -s tests -v` passe avec `48` tests

## Faits live du 14 mars 2026

### Apple

- warm-up direct sur `apple-coreml:qwen3.5-4b-onnx-q4f16` via `:8100/v1/chat/completions`: `2.76s`
- requete prose plus representative (`max_tokens=96`) sur le meme modele: `39.99s`
- conclusion: le runtime Apple n'est pas mort; il est lent mais exploitable

### Ollama natif

- `ollama` 0.17.7 sur macOS 26.3.1 / Apple M5 echoue encore en generation sur `qwen2.5:7b` et `qwen2.5:1.5b`
- les deux reports cibles du 14 mars tombent en `provider_failed` / `ollama_runtime_unhealthy`
- le symptome utile cote projet est `HTTP 500 Internal Server Error`

### Contournement valide

- `llama-server` local sait charger directement le blob GGUF Ollama de `qwen2.5:1.5b`
- un serveur temporaire sur `127.0.0.1:8082` a repondu en `0.31s`
- implication: le blocage n'est pas le modele lui-meme, mais le runtime Ollama natif

## Ce qui est vraiment bloque

Le projet n'est plus bloque par le pipeline narratif.

Le vrai blocage est maintenant:

- comment servir `qwen2.5:1.5b` et `qwen2.5:7b` via un backend local stable
- sans perdre le routage `provider:model` attendu par `mascarade` et `ai-novel-engine`

## Hypothese de travail la plus rentable

La piste la plus prometteuse n'est plus "reparer les prompts" mais:

1. brancher un chemin `llama.cpp` / `llama-server` reutilisable pour les blobs `qwen2.5`
2. rerun `priority_models` et `baselines`
3. reprendre `rewrite` / `repair` seulement sur les blockers qui survivent apres stabilisation runtime

## Fichiers a ouvrir en premier

- `docs/MEMOIRE_REPRISE_2026-03-14.md`
- `docs/EXECUTION_PLAN_2026-03-14.md`
- `TODO_ACTIVE.md`
- `docs/MODEL_COMPARISON_2026-03-08.md`
- `automation/reports/20260314T085946Z/SUMMARY.md`
- `automation/reports/20260314T100648Z/SUMMARY.md`

