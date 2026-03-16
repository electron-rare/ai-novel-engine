# Memoire de reprise - 14 mars 2026

Memoire operationnelle pour reprendre `ai-novel-engine` sans refaire toute l'enquete runtime.

## Etat confirme

- la suite locale passe avec `48` tests
- la reference locale reste `apple-coreml:qwen3.5-4b-onnx-q4f16`
- `apple-coreml:qwen2.5-0.5b-instruct-onnx` reste `quality_blocked` sur un blocage de fin / garde-fou
- `ollama:qwen2.5:7b` est maintenant a lire comme un blocage runtime, pas comme un simple blocage qualite
- `ollama:qwen2.5:1.5b` est dans le meme etat runtime que le 7b

## Reports du 14 mars 2026 a retenir

- `automation/reports/20260314T085946Z`:
  - `ollama:qwen2.5:7b` -> `provider_failed`
  - `status=ollama_runtime_unhealthy`
  - note utile: `HTTP 500 Internal Server Error`
- `automation/reports/20260314T100648Z`:
  - `ollama:qwen2.5:1.5b` -> `provider_failed`
  - meme symptome utile: `HTTP 500 Internal Server Error`

## Mesures live utiles

- Apple warm-up direct sur `:8100`: `2.76s`
- Apple requete prose representative (`96` tokens): `39.99s`
- `llama-server` temporaire sur le blob `qwen2.5:1.5b`: reponse en `0.31s`

## Ce que cela veut dire

- Apple n'est pas le sujet critique du jour
- Ollama natif 0.17.7 reste le composant qui casse
- les blobs GGUF `qwen2.5` presents dans `~/.ollama/models/blobs/` sont sains et reutilisables via `llama.cpp`

## Decision de reprise

- ne plus perdre du temps a tuner `rewrite` / `repair` tant que les reruns `qwen2.5` passent par un runtime instable
- prioriser un contournement `llama-server` / `llama.cpp` avant tout nouveau lot comparatif
- garder `apple-coreml:qwen3.5-4b-onnx-q4f16` comme reference stable

## Fichiers et chemins utiles

- blob `qwen2.5:1.5b`: `/Users/electron/.ollama/models/blobs/sha256-183715c435899236895da3869489cc30ac241476b4971a20285b1a462818a5b4`
- blob `qwen2.5:7b`: `/Users/electron/.ollama/models/blobs/sha256-2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730`
- report `7b`: `automation/reports/20260314T085946Z/`
- report `1.5b`: `automation/reports/20260314T100648Z/`
- comparatif courant: `docs/MODEL_COMPARISON_2026-03-08.md`

## Prochaine action utile

Rendre le contournement `llama.cpp` reusable cote runtime, puis rejouer:

```bash
python3 scripts/run_next_lots.py --lot priority_models
python3 scripts/run_next_lots.py --lot baselines
```

